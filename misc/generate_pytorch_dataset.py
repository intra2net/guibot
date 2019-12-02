#!/usr/bin/python3

"""
PyTorch dataset maker script
----------------------------
Purpose: This script can be used to generate a dataset compatible with PyTorch datasets.
Dependencies: PIL, torch

Must be provided before run: folder of positive and negative images, list of positive and negative images
Will be provided after run: a .pth file with the data to be loaded when training and testing the network

Note: This script can reuse augmented data and relies on list format similar to the one of `generate_cascade.sh`.

Note: The network input and output layer sizes have been selected according to the current memory capacity of 32GB.
The output layer size defines the precision of the localization performed by the network while the input layer size
defines the resolution of detected features.
"""

import argparse
import os
import torch
import torchvision.transforms as transforms
from PIL import Image


parser = argparse.ArgumentParser(description='PyTorch dataset maker script')
parser.add_argument('--imglist', default='images.lst', help='List with image paths and annotation regions')
parser.add_argument('--isize', default='150x150', help='Sample image size of the type WIDTHxHEIGHT')
parser.add_argument('--osize', default='15x15', help='Target image size of the type WIDTHxHEIGHT')
parser.add_argument('--output', default='images.pth', help='Output filename for the created tensors')
args = parser.parse_args()


def tensors_from_data():
    """
    Get a samples and targets tensor from a folder of images and an
    annotated list with their filenames and regions where the object
    is detected.
    """
    if not os.path.exists(args.imglist):
        raise IOError("No image list with the name '%s' can be found" % args.imglist)
    with open(args.imglist) as f:
        lines = f.read().splitlines()

    iwidth, iheight = [int(s) for s in args.isize.split("x")]
    owidth, oheight = [int(s) for s in args.osize.split("x")]
    samples = torch.Tensor(len(lines), 1, iheight, iwidth)
    targets = torch.LongTensor(len(lines))

    for i, line in enumerate(lines):
        words = line.split(" ")
        if len(words) == 6:
            # this is a positive (annotated) image (unless 0)
            image_path = words[0]
            region_num = int(words[1])
            region_x, region_y = int(words[2]), int(words[3])
            region_w, region_h = int(words[4]), int(words[5])
        elif len(words) == 1:
            # this is a negative (background) image
            image_path = words[0]
            region_num = 0
            region_x, region_y = 0, 0
            region_w, region_h = 0, 0
        else:
            raise ValueError("Corrupted line %i in text file - must be space separated with image path" % i)
        print("Extracted region number", region_num, "for line", i)

        # image path is relative to the list file
        sample = Image.open(os.path.join(os.path.dirname(args.imglist), image_path))
        width, height = sample.width, sample.height
        sample = sample.resize((iwidth, iheight))
        sample = sample.convert('L') if sample.mode != 'L' else sample
        converter = transforms.ToTensor()
        samples[i,0,...] = converter(sample)

        target = owidth * oheight
        if region_w != 0 and region_h != 0:
            target_x = int(region_x * float(owidth) / width)
            target_y = int(region_y * float(oheight) / height)
            target = target_y * owidth + target_x
        targets[i] = target

    return samples, targets


if __name__ == '__main__':
    print("Compiling images into a dataset... (this may take a while)")
    samples, targets = tensors_from_data()

    samples_filename = "samples_" + args.output
    print("Saving samples (", samples.size(), ") to ", os.path.abspath(samples_filename))
    torch.save(samples, samples_filename)

    targets_filename = "targets_" + args.output
    print("Saving targets (", targets.size(), ") to ", os.path.abspath(targets_filename))
    torch.save(targets, targets_filename)
