import random
import shutil

from anyio import Path
from pathlib import Path


def split_pairs_into_train_val_test(source_dir, output_dir, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, seed=42, move_files=False):
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)

    if abs((train_ratio + val_ratio + test_ratio) - 1.0) > 1e-8:
        raise ValueError('train_ratio, val_ratio, and test_ratio must sum to 1.0')

    rng = random.Random(seed)
    split_names = ('train', 'val', 'test')

    for split_name in split_names:
        for label_name in ('sim', 'diff'):
            (output_dir / split_name / label_name).mkdir(parents=True, exist_ok=True)

    for label_name in ('sim', 'diff'):
        label_dir = source_dir / label_name
        if not label_dir.exists():
            continue

        pair_bases = []
        for image1_path in sorted(label_dir.glob('*_0.*')):
            if not image1_path.stem.endswith('_0'):
                continue
            image2_name = image1_path.stem[:-2] + '_1' + image1_path.suffix
            image2_path = image1_path.with_name(image2_name)
            if image2_path.exists():
                pair_bases.append(image1_path.stem[:-2])

        rng.shuffle(pair_bases)
        total_pairs = len(pair_bases)
        train_count = int(total_pairs * train_ratio)
        val_count = int(total_pairs * val_ratio)
        test_count = total_pairs - train_count - val_count

        split_assignments = (
            ('train', pair_bases[:train_count]),
            ('val', pair_bases[train_count:train_count + val_count]),
            ('test', pair_bases[train_count + val_count:train_count + val_count + test_count]),
        )

        for split_name, bases in split_assignments:
            target_dir = output_dir / split_name / label_name
            for base_name in bases:
                for suffix in ('_0', '_1'):
                    source_file = next(label_dir.glob(f'{base_name}{suffix}.*'), None)
                    if source_file is None:
                        continue
                    target_file = target_dir / source_file.name
                    if move_files:
                        shutil.move(str(source_file), str(target_file))
                    else:
                        shutil.copy2(source_file, target_file)