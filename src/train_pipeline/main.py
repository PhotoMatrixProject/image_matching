import torch
import model as m


def run_training_pipeline(
    data_root,
    num_epochs=10,
    batch_size=8,
    learning_rate=1e-4,
    num_workers=0,
    backbone_name='vit_base_patch16_dinov3.lvd1689m',
    pretrained=True,
    freeze_backbone=False,
    checkpoint_path='checkpoints/best_model.pt',
    device=None,
):
    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    model = m.SiameseCosineModel(
        backbone_name=backbone_name,
        pretrained=pretrained,
        freeze_backbone=freeze_backbone,
    ).to(device)

    train_loader, val_loader, test_loader = m.build_dataloaders(
        data_root=data_root,
        model=model,
        batch_size=batch_size,
        num_workers=num_workers,
        shuffle_train=True,
    )

    if len(train_loader.dataset) == 0:
        raise ValueError('Train split is empty. Check folder structure and pair naming: *_0 and *_1.')
    if len(val_loader.dataset) == 0:
        raise ValueError('Val split is empty. Check folder structure and pair naming: *_0 and *_1.')
    if len(test_loader.dataset) == 0:
        raise ValueError('Test split is empty. Check folder structure and pair naming: *_0 and *_1.')

    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=learning_rate,
    )

    model = m.fit(
        model=model,
        train_dataloader=train_loader,
        val_dataloader=val_loader,
        optimizer=optimizer,
        num_epochs=num_epochs,
        device=device,
        checkpoint_path=checkpoint_path,
    )

    criterion = torch.nn.BCEWithLogitsLoss()
    train_loss, train_acc, _, _ = m.evaluate(train_loader, model, criterion, device)
    val_loss, val_acc, _, _ = m.evaluate(val_loader, model, criterion, device)
    test_loss, test_acc, _, _ = m.evaluate(test_loader, model, criterion, device)

    print('----- Final metrics -----')
    print(f'train: loss={train_loss:.4f} acc={train_acc:.4f}')
    print(f'val:   loss={val_loss:.4f} acc={val_acc:.4f}')
    print(f'test:  loss={test_loss:.4f} acc={test_acc:.4f}')
    print(f'learned threshold={model.threshold.item():.4f}')
    print(f'best state path={checkpoint_path}')

    return {
        'model': model,
        'device': device,
        'metrics': {
            'train': {'loss': train_loss, 'acc': train_acc},
            'val': {'loss': val_loss, 'acc': val_acc},
            'test': {'loss': test_loss, 'acc': test_acc},
        },
        'threshold': model.threshold.item(),
        'checkpoint_path': checkpoint_path,
    }


# if __name__ == '__main__':
    # run_training_pipeline(
    #     data_root=r'.\data',
    #     num_epochs=5,
    #     batch_size=8,
    #     learning_rate=1e-4,
    #     num_workers=0,
    #     checkpoint_path=r'.\checkpoints\best_model.pt',
    # )