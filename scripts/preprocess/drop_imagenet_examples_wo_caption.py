import sys
import os
import json
import shutil
import argparse
from tqdm import tqdm

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))

from utils import logging_utils as logu
from utils.logging_utils import print_verbose


if __name__ == '__main__':
    # ----- Get arguments from input -----
    parser = argparse.ArgumentParser()

    # ----- Settings -----
    parser.add_argument('--load_path', type=str, default=os.path.join('imagenet-captions', 'imagenet_captions.json'))
    parser.add_argument('--images_path', type=str, default=os.path.join('ilsvrc2012', 'ILSVRC2012_img_train'))
    parser.add_argument('--selected_images_path', type=str, default=os.path.join('ilsvrc2012', 'ILSVRC2012_img_train_selected'))

    # Convert to dictionary
    params = vars(parser.parse_args())

    # ----- Init -----
    logu.verbose = True

    # ----- Load -----
    # Imagenet-captions
    print_verbose('loading imagenet-captions ...')

    imagenet_captions_path = params['load_path']
    images_path = params['images_path']
    selected_images_path = params['selected_images_path']

    with open(imagenet_captions_path, 'rb') as f:
        imagenet_captions = json.load(f)

    print_verbose('done!\n')

    # ----- Find images with caption -----
    ic_file_names = [ic['filename'] for ic in imagenet_captions]

    # replace ext ".JPEG" with ".jpg"
    ic_file_names = [file_name.replace('.JPEG', '.jpg') for file_name in ic_file_names]

    # remain unique paths only
    ic_file_names = list(set(ic_file_names))

    for file_name in tqdm(ic_file_names):
        shutil.copy2(os.path.join(images_path, file_name), os.path.join(selected_images_path, file_name))
