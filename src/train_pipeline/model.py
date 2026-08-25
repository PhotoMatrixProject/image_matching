from __future__ import annotations

from pathlib import Path
from PIL import Image
import timm
import torch
import torch.nn.functional as F

# Image.MAX_IMAGE_PIXELS = None  # Disable DecompressionBombError

class PairDataset(torch.utils.data.Dataset):
    def __init__(self, image_pairs, transforms=None):
        self.image_pairs = image_pairs
        self.transforms = transforms

    def __len__(self):
        return len(self.image_pairs)

    def __getitem__(self, idx):
        img1_path, img2_path, label = self.image_pairs[idx]
        img1 = Image.open(img1_path).convert('RGB')
        img2 = Image.open(img2_path).convert('RGB')

        if self.transforms is not None:
            img1 = self.transforms(img1)
            img2 = self.transforms(img2)

        return img1, img2, torch.tensor(label, dtype=torch.float32)


def load_pairs_from_split(split_dir):
    split_dir = Path(split_dir)
    image_pairs = []

    for label_name, label in (('sim', 1), ('diff', 0)):
        label_dir = split_dir / label_name
        if not label_dir.exists():
            continue

        for image1_path in sorted(label_dir.glob('*_0.*')):
            if not image1_path.stem.endswith('_0'):
                continue

            image2_name = image1_path.stem[:-2] + '_1' + image1_path.suffix
            image2_path = image1_path.with_name(image2_name)

            if image2_path.exists():
                image_pairs.append((str(image1_path), str(image2_path), label))

    return image_pairs


def build_dataloaders(data_root, model, batch_size=8, num_workers=0, shuffle_train=True):
    data_root = Path(data_root)

    train_dataset = PairDataset(load_pairs_from_split(data_root / 'train'), transforms=model.transforms)
    val_dataset = PairDataset(load_pairs_from_split(data_root / 'val'), transforms=model.transforms)
    test_dataset = PairDataset(load_pairs_from_split(data_root / 'test'), transforms=model.transforms)

    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=shuffle_train,
        num_workers=num_workers,
    )
    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )
    test_loader = torch.utils.data.DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    return train_loader, val_loader, test_loader


class SiameseCosineModel(torch.nn.Module):
    def __init__(self, backbone_name='vit_base_patch16_dinov3.lvd1689m', pretrained=True, freeze_backbone=False):
        super().__init__()
        self.encoder = timm.create_model(
            backbone_name,
            pretrained=pretrained,
            num_classes=0,
        )

        if freeze_backbone:
            for parameter in self.encoder.parameters():
                parameter.requires_grad = False

        data_config = timm.data.resolve_model_data_config(self.encoder)
        self.transforms = timm.data.create_transform(**data_config, is_training=False)

        self.threshold = torch.nn.Parameter(torch.tensor(0.5))
        self.logit_scale = torch.nn.Parameter(torch.tensor(10.0))

    def encode(self, images):
        return self.encoder(images)

    def forward(self, images1, images2):
        embeddings1 = self.encode(images1)
        embeddings2 = self.encode(images2)
        cosine_similarity = F.cosine_similarity(embeddings1, embeddings2, dim=-1)
        scale = F.softplus(self.logit_scale) + 1e-6
        logits = scale * (cosine_similarity - self.threshold)
        return logits, cosine_similarity


def train_one_epoch(dataloader, model, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images1, images2, labels in dataloader:
        images1 = images1.to(device)
        images2 = images2.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        logits, cosine_similarity = model(images1, images2)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * labels.size(0)
        predictions = (torch.sigmoid(logits) >= 0.5).float()
        correct += (predictions == labels).sum().item()
        total += labels.size(0)

    return running_loss / max(total, 1), correct / max(total, 1)


@torch.no_grad()
def evaluate(dataloader, model, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    cosine_scores = []
    labels_out = []

    for images1, images2, labels in dataloader:
        images1 = images1.to(device)
        images2 = images2.to(device)
        labels = labels.to(device)

        logits, cosine_similarity = model(images1, images2)
        loss = criterion(logits, labels)

        running_loss += loss.item() * labels.size(0)
        predictions = (torch.sigmoid(logits) >= 0.5).float()
        correct += (predictions == labels).sum().item()
        total += labels.size(0)

        cosine_scores.append(cosine_similarity.detach().cpu())
        labels_out.append(labels.detach().cpu())

    return (
        running_loss / max(total, 1),
        correct / max(total, 1),
        torch.cat(cosine_scores) if cosine_scores else torch.empty(0),
        torch.cat(labels_out) if labels_out else torch.empty(0),
    )


def find_best_threshold(cosine_scores, labels, num_steps=200):
    if cosine_scores.numel() == 0:
        return 0.5

    thresholds = torch.linspace(-1.0, 1.0, steps=num_steps)
    best_threshold = thresholds[0]
    best_accuracy = -1.0

    labels = labels.float()
    for threshold in thresholds:
        predictions = (cosine_scores >= threshold).float()
        accuracy = (predictions == labels).float().mean().item()
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold

    return float(best_threshold)


def fit(model, train_dataloader, val_dataloader, optimizer, num_epochs, device, checkpoint_path=None):
    criterion = torch.nn.BCEWithLogitsLoss()
    best_val_accuracy = -1.0
    best_state = None
    best_epoch = -1

    for epoch in range(num_epochs):
        train_loss, train_accuracy = train_one_epoch(train_dataloader, model, criterion, optimizer, device)
        val_loss, val_accuracy, val_scores, val_labels = evaluate(val_dataloader, model, criterion, device)

        learned_threshold = find_best_threshold(val_scores, val_labels)
        model.threshold.data.fill_(learned_threshold)

        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            best_epoch = epoch + 1

            if checkpoint_path is not None:
                checkpoint_path = Path(checkpoint_path)
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save(
                    {
                        'epoch': best_epoch,
                        'val_accuracy': best_val_accuracy,
                        'model_state_dict': best_state,
                        'threshold': float(best_state['threshold']),
                    },
                    checkpoint_path,
                )

        print(
            f"epoch={epoch + 1} train_loss={train_loss:.4f} train_acc={train_accuracy:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_accuracy:.4f} threshold={learned_threshold:.4f}"
        )

    if best_state is not None:
        model.load_state_dict(best_state)

    if checkpoint_path is not None and best_state is not None:
        print(f"best checkpoint saved to {checkpoint_path} (epoch={best_epoch}, val_acc={best_val_accuracy:.4f})")

    return model

def load_pretrained_model(checkpoint_path, backbone_name='vit_base_patch16_dinov3.lvd1689m', pretrained=True, freeze_backbone=False, device=None):
    model = SiameseCosineModel(backbone_name=backbone_name, pretrained=pretrained, freeze_backbone=freeze_backbone)
    if device is not None:
        model.to(device)

    checkpoint_path = Path(checkpoint_path)
    if checkpoint_path.exists():
        checkpoint = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.threshold.data.fill_(checkpoint.get('threshold', 0.5))
        print(model.threshold)
        print(f"Loaded pretrained model from {checkpoint_path} (epoch={checkpoint.get('epoch', 'N/A')}, val_acc={checkpoint.get('val_accuracy', 'N/A'):.4f})")
    else:
        print(f"No checkpoint found at {checkpoint_path}. Using randomly initialized model.")

    return model

@torch.no_grad()
def predict(model, dataloader, device, threshold=0.4372):
    model.eval()
    outputs = []

    for images1, images2, _ in dataloader:
        images1 = images1.to(device)
        images2 = images2.to(device)
        logits, cosine_similarity = model(images1, images2)
        probabilities = torch.sigmoid(logits)
        predictions = (cosine_similarity >= threshold).float()
        outputs.append((cosine_similarity.cpu(), probabilities.cpu(), predictions.cpu()))

    return outputs
