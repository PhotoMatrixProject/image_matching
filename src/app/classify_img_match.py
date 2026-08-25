from __future__ import annotations
from collections import Counter

from pyexpat import model
import random
import shutil
from pathlib import Path
from typing import Sequence
import os
from PIL import Image
import timm
import torch
import torch.nn.functional as F


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



class ClassificationTool:
    def __init__(self, classification_path: str):
        self.classification_path = classification_path
        self.class_names = ['sim', 'dif']
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.big_model = self.load_pretrained_model(
            # r'.\model\best_model1.pt',
            r'.\model\best_model_b4.pt',
            device=self.device,
        )
        self.threshold=self.big_model.threshold.item()

        self.sim_counter = len(os.listdir(os.path.join(self.classification_path, 'sim')))//2 if os.path.exists(os.path.join(self.classification_path, 'sim')) else 0
        self.dif_counter = len(os.listdir(os.path.join(self.classification_path, 'dif')))//2 if os.path.exists(os.path.join(self.classification_path, 'dif')) else 0
        # print(type(self.big_model))
        # print(self.big_model.forward)

    def load_pretrained_model(self, checkpoint_path, backbone_name='vit_base_patch16_dinov3.lvd1689m', pretrained=True, freeze_backbone=False, device=None):
        model = SiameseCosineModel(backbone_name=backbone_name, pretrained=pretrained, freeze_backbone=freeze_backbone)
        if device is not None:
            model.to(device)

        checkpoint_path = Path(checkpoint_path)
        if checkpoint_path.exists():
            checkpoint = torch.load(checkpoint_path, map_location=device)
            model.load_state_dict(checkpoint['model_state_dict'])
            model.threshold.data.fill_(checkpoint.get('threshold', 0.5))
            model.eval()
            print(model.threshold)
            print(f"Loaded pretrained model from {checkpoint_path} (epoch={checkpoint.get('epoch', 'N/A')}, val_acc={checkpoint.get('val_accuracy', 'N/A'):.4f})")
        else:
            print(f"No checkpoint found at {checkpoint_path}. Using randomly initialized model.")

        return model

    def predict(self, img1_path:str, img2_path:str):
        transforms = self.big_model.transforms
        img1 = Image.open(img1_path).convert('RGB')
        img2 = Image.open(img2_path).convert('RGB')
        with torch.no_grad():
            images1 = transforms(img1).unsqueeze(0).to(self.device)
            images2 = transforms(img2).unsqueeze(0).to(self.device)
            logits, cosine_similarity = self.big_model(images1, images2)
            probabilities = torch.sigmoid(logits)
            pred = (cosine_similarity >= self.threshold).float()

        return pred

    def save_orig_img_to_class_folder(self, img1_path:str, img2_path:str, img_class:str):
        try:
            print("Copying ", img1_path, " to: ", os.path.join(self.classification_path, img_class))
            if not os.path.exists(os.path.join(self.classification_path, img_class)):
                os.mkdir(os.path.join(self.classification_path, img_class))
            shutil.copy(img1_path, os.path.join(self.classification_path, img_class))
            os.rename(os.path.join(self.classification_path, img_class, os.path.basename(img1_path)), 
                      os.path.join(self.classification_path, img_class, f"{img_class}_{self.sim_counter if img_class == 'sim' else self.dif_counter}_0.jpeg"))
            
            shutil.copy(img2_path, os.path.join(self.classification_path, img_class))
            os.rename(os.path.join(self.classification_path, img_class, os.path.basename(img2_path)), 
                      os.path.join(self.classification_path, img_class, f"{img_class}_{self.sim_counter if img_class == 'sim' else self.dif_counter}_1.jpeg"))

            if img_class == 'sim':
                self.sim_counter += 1
            else:
                self.dif_counter += 1
        except Exception as e:
            print("An error occurred while copying to class folder...", e)
        return

    def get_classification_rank(self, img_path1:str, img_path2:str)->list:
        pred = self.predict(img_path1, img_path2)
        if pred.item() == 1.0:
            self.save_orig_img_to_class_folder(img_path1, img_path2, 'sim')
            return [('sim')]
        else:
            self.save_orig_img_to_class_folder(img_path1, img_path2, 'dif')
            return [('dif')]
