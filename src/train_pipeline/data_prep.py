import os
import shutil
import torchvision.transforms as transforms
from PIL import Image

def create_pairs_from_folder(folder_path:str, dest_path:str, num:int):
    imgs = os.listdir(folder_path)
    imgs = [img for img in imgs if img.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if len(imgs) % 2 == 0:
        pair_num = len(imgs) // 2
        for i in range(pair_num):
            print(num)
            img1 = os.path.join(folder_path, imgs[i])
            img2 = os.path.join(folder_path, imgs[i+1])
            shutil.copy(img1, os.path.join(dest_path, f'{num}_0.jpeg'))
            shutil.copy(img2, os.path.join(dest_path, f'{num}_1.jpeg'))
            num += 1
    else:
        pair_num = (len(imgs) - 1) // 2
        for i in range(pair_num):
            print(num)
            img1 = os.path.join(folder_path, imgs[i])
            img2 = os.path.join(folder_path, imgs[i+1])
            shutil.copy(img1, os.path.join(dest_path, f'{num}_0.jpeg'))
            shutil.copy(img2, os.path.join(dest_path, f'{num}_1.jpeg'))
            num += 1
        shutil.copy(os.path.join(folder_path, imgs[-1]), os.path.join(dest_path, f'{num}_0.jpeg'))
        shutil.copy(os.path.join(folder_path, imgs[0]), os.path.join(dest_path, f'{num}_1.jpeg'))
        num += 1
    return num


def create_pairs_from_folders(folder:str, dest:str):
    num = 1178
    folders = os.listdir(folder)
    folders = [fol for fol in folders if not fol.endswith('_remove')]
    for fol in folders:
        folder_path = os.path.join(folder, fol)
        print(folder_path)
        num = create_pairs_from_folder(folder_path, dest, num)


def rename_files_in_folder(folder_path:str):
    start_num = 6270
    imgs = os.listdir(folder_path)
    imgs = [img for img in imgs if img.lower().endswith(('.jpg', '.jpeg', '.png'))]
    imgs_0 = [img for img in imgs if img.endswith('_0.jpeg') or img.endswith('_0.jpg') or img.endswith('_0.png')]
    imgs_1 = [img for img in imgs if img.endswith('_1.jpeg') or img.endswith('_1.jpg') or img.endswith('_1.png')]
    for i, (img0, img1) in enumerate(zip(imgs_0, imgs_1)):
        if img0[:-6] != img1[:-6]:
            print(f"Warning: Mismatched pair {img0} and {img1}. Skipping.")
            continue
        print(start_num + i)
        old_path0 = os.path.join(folder_path, img0)
        old_path1 = os.path.join(folder_path, img1)
        new_path0 = os.path.join(folder_path, f'{i+start_num}_0.jpeg')
        new_path1 = os.path.join(folder_path, f'{i+start_num}_1.jpeg')
        os.rename(old_path0, new_path0)
        os.rename(old_path1, new_path1)


def create_pairs_against_one_image(folder_path:str, dest_path:str, num:int):
    imgs = os.listdir(folder_path)
    imgs = [img for img in imgs if img.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if len(imgs) < 2:
        print("Not enough images to create pairs.")
        return num
    base_name = os.path.basename(folder_path)
    base_name_pool = [base_name + ext for ext in ['.jpg', '.jpeg', '.png']]
    base_img = [img for img in imgs if img in base_name_pool]
    if len(base_img) == 0:
        print(f"No base image found in {folder_path}.")
        return num
    base_path = os.path.join(folder_path, base_img[0])
    for i in range(len(imgs)):
        if imgs[i] == base_img[0]:
            continue
        print(num)
        img2 = os.path.join(folder_path, imgs[i])
        shutil.copy(base_path, os.path.join(dest_path, f'{num}_0.jpeg'))
        shutil.copy(img2, os.path.join(dest_path, f'{num}_1.jpeg'))
        num += 1
    return num

def apply_create_pairs_against_one_image(folder:str, dest:str):
    num = 592
    folders = os.listdir(folder)
    for fol in folders:
        folder_path = os.path.join(folder, fol)
        print(folder_path)
        num = create_pairs_against_one_image(folder_path, dest, num)




def resize_and_save_img(img_path:str, destination:str, num:int):
    '''Resizes image to 256x256 and saves new image in the destination.'''
    try:
        tr = transforms.Resize((512, 512), interpolation=transforms.InterpolationMode.BICUBIC)
        crop_img1 = Image.open(img_path)
        if crop_img1.height == 512 and crop_img1.width == 512: return
        if crop_img1.mode != 'RGB':
            crop_img1 = crop_img1.convert('RGB')
        crop_img1 = tr.forward(crop_img1)
        crop_img1.save(img_path.replace('.jpg', '.jpeg'))
        return
    except Exception:
        print("Error with:", img_path)
        return


def resize_batch(source_dir:str, destination:str, num:int):
    '''Creates a new folder (destination) with cropped images from the source dir.'''
    imgs = os.listdir(source_dir)
    for i in range(len(imgs)):
        path = os.path.join(source_dir, imgs[i])
        if os.path.isfile(path):
            if imgs[i].endswith('jpeg') or imgs[i].endswith('png') or imgs[i].endswith('jpg'):
                resize_and_save_img(path, source_dir, num)
                num += 1
                print(num)
    return num


def create_data_dir(source_dir:str, destination:str, num:int):
    '''Takes a forlder with class folders and crops all the images in the class folders.'''
    dirs = os.listdir(source_dir)
    for i in range(len(dirs)):
        path = os.path.join(source_dir, dirs[i])
        num = resize_batch(path, path, num)

    return num

