#!/usr/bin/python3

# Only needed if not installed system wide
import sys
sys.path.insert(0, '../..')


"""
Program start here
----------------------------

Create a deep network capable of locating given button classes.

This example demonstrates all following steps - defining any dataset handling,
network's training, testing, configuration, and reuse for a specific matching.


Current synthetic dataset
----------------------------
The locally defined dataset class generates screenshots with various buttons
placed at various locations.

Must be provided before run: folder of source/root images
Will be provided after run: a .pth file with the trained network model


Transfer learning
----------------------------
The locally defined pipeline can be used for transfer learning, i.e. reusing a
pretrained text detection model (e.g. on the COCO dataset) and retraining it
for a new set of classes, in the current example buttons.

For more details on the finetuning process itself, you can check:

https://pytorch.org/tutorials/intermediate/torchvision_tutorial.html
"""

import logging
import shutil
import argparse
import random
import itertools
import os
import multiprocessing
import PIL
import numpy

import torch
import torch.optim as optim
import torch.nn as nn
from torch.utils.data import Dataset, Subset, DataLoader
import torchvision.transforms as transforms
from tqdm import tqdm

from guibot.config import GlobalConfig
from guibot.imagelogger import ImageLogger
from guibot.fileresolver import FileResolver
from guibot.target import Pattern, Image
from guibot.finder import DeepFinder
from guibot.errors import *


# Target data paths
file_resolver = FileResolver()
file_resolver.add_path('images/')


# Overall logging setup
LOGPATH = './tmp/'
REMOVE_LOGPATH = False
DUMP_DATASET_ITEMS = False
os.makedirs(LOGPATH, exist_ok=True)
handler = logging.StreamHandler()
logging.getLogger('').addHandler(handler)
logging.getLogger('').setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
GlobalConfig.image_logging_level = 0
GlobalConfig.image_logging_destination = LOGPATH
GlobalConfig.image_logging_step_width = 4
ImageLogger.step = 1


# Reproducible randomness (e.g. validation split, etc.)
SEED = 42
random.seed(SEED)
os.environ['PYTHONHASHSEED'] = str(SEED)
numpy.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed(SEED)


class SyntheticDataset(Dataset):
    """
    A synthetic dataset with generated images with buttons at different positions.

    The dataset uses an original selection of images of different classes and
    can generate images with a different number of randomly placed buttons.
    """
    def __init__(self, path=None, width=500, height=500, delta=5,
                 buttons_min=1, buttons_max=1, size_min=-5, size_max=10,
                 transform=None):
        super().__init__()

        self.path = path if path is not None else "."
        # there is always a background (non-object) class in the detection
        self.classes = ["__background__"]
        self._rootimgs = {}
        for imgpath in os.listdir(self.path):
            if imgpath.endswith(".steps"):
                class_name = os.path.splitext(imgpath)[0]
                self.classes.append(class_name)
                with open(os.path.join(self.path, imgpath)) as f:
                    images = [l.split('\t')[0] for l in f.readlines()]
                self._rootimgs[class_name] = [PIL.Image.open(os.path.join(self.path, i)) for i in images]
        assert len(self._rootimgs.keys()) > 0, "There must be at least some generating images"

        self.width = width
        self.height = height

        self.button_number_range = (buttons_min, buttons_max+1)
        self.button_size_range = (size_min, size_max+1)

        button_states = []
        for c in range(1, len(self.classes)):
            for x in range(0, self.width, delta):
                for y in range(0, self.height, delta):
                    button_states.append((c, x, y))

        self._idefs = []
        for buttons in range(*self.button_number_range):
            self._idefs += [i for i in itertools.product(button_states, repeat=buttons)]

        self.transform = transform

    def __len__(self):
        return len(self._idefs)

    def __getitem__(self, i):
        background = PIL.Image.new('RGB', (self.width, self.height), color=(240, 240, 240))
        boxes, labels = [], []

        # Generate an image of differently positioned buttons
        # TODO: there is a chance of overlapping but it is relatively small for
        # larger screens and thus not worth complicating this any further with
        for j in range(len(self._idefs[i])):
            c, x, y = self._idefs[i][j]

            # Scale the button with a allowable size variation
            button = random.choice(self._rootimgs[self.classes[c]])
            ratio = button.width / button.height
            ds = random.randint(*self.button_size_range)
            button = button.resize((button.width+int(ratio*ds), button.height+ds))

            # Paste the selected button and make sure it is not cropped
            new_width, new_height = x + button.width, y + button.height
            if new_width > background.width or new_height > background.height:
                new_width = max(new_width, background.width)
                new_height = max(new_height, background.height)
                # NOTE: the background is stretched to accommodate buttons
                # as it represents a general region of the screen anyway
                new_background = PIL.Image.new('RGB', (new_width, new_height),
                                               color=(240, 240, 240))
                new_background.paste(background)
                background = new_background
                del new_background
            background.paste(button, (x, y))

            # Calculate the bounding box and label of the current button
            boxes += [(x, y, x + button.width, y + button.height)]
            labels += [c]

        # Obtain a final screenshot image with all buttons
        if DUMP_DATASET_ITEMS:
            background.save(os.path.join(LOGPATH, f"screen_item_{i}.png"))
        image = numpy.asarray(background)

        if self.transform:
            image = self.transform(image)
        target = {'boxes': torch.as_tensor(boxes, dtype=torch.int64),
                  'labels': torch.as_tensor(labels, dtype=torch.int64)}

        return image, target

    def summary(self, train=False):
        """
        Print a summary of the loaded dataset.

        :param bool train: whether the dataset is a train set or test set
        """
        summary = [f"Total number of {'train' if train else 'test'} samples: {len(self)}"]
        summary += [f"Detected classes ({len(self.classes)}): {', '.join(self.classes)}"]
        summary += [f"Image shape (width, height, channels): {self.width}x{self.height}x3"]
        summary += [f"Number of buttons: from {self.button_number_range[0]} to {self.button_number_range[1]-1}"]
        summary += [f"Size variation of buttons: from {self.button_size_range[0]} to {self.button_size_range[1]-1}"]
        image_stats = [len(self._rootimgs[c]) for c in self.classes if c != "__background__"]
        summary += [f"Image variation of buttons: from {min(image_stats)} to {max(image_stats)}"]
        return os.linesep.join(summary)


def train(epoch, model, train_loader, device, hyperparams):
    """
    Train the neural network model.

    :param int epoch: number of the current training epoch
    :param model: PyTorch model to be trained
    :type: :py:class:`torch.nn.Module`
    :param train_loader: train loader providing all mini-batches
    :type train_loader: :py:class:`DataLoader`
    :param device: device to send the model and data to
    :type device: :py:class:`torch.device`
    :param hyperparams: training hyper-parameters
    :type: {str, str}
    """
    # Initialize stochastic gradient descent optimizer for learning
    optimizer = optim.SGD(model.parameters(),
                          lr=hyperparams["learning_rate"],
                          momentum=hyperparams["sgd_momentum"])
    lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer,
                                                   step_size=hyperparams["step_size"],
                                                   gamma=hyperparams["gamma"])

    # Resend model to device including its new detector head
    model.to(device)
    # Set the module in training mode
    model.train()

    for i, (images, targets) in enumerate(train_loader):
        inputs = [image.to(device) for image in images]
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        # This is the forward pass to be followed by a backward (update) pass
        optimizer.zero_grad()
        losses = model(inputs, targets)

        # Backpropagation is done for four loss functions
        # NOTE: this assumes no mixed precision is used
        total_loss = sum(loss for loss in losses.values())
        total_loss.backward()
        # Update weights (optimization parameters)
        optimizer.step()
        # Update learning rate (optimization step)
        lr_scheduler.step()

        # Log measurements on each few mini-batches for brevity
        if i % hyperparams["log_interval"] == 0:
            losses_str = " ".join("{} ({:.6f})".format(*item) for item in losses.items())
            logging.info(f"Train Epoch: {epoch} [{(i+1) * hyperparams['batch_size']}/{len(train_loader.dataset)}"
                         f" ({100 * (i+1) / len(train_loader):.0f}%)]\tLosses: {losses_str}")

        # Save the network state on each few mini-batches if required
        if i % hyperparams["save_interval"] == 0 and hyperparams["model_checkpoint"] is not None:
            logging.debug(f"Saving model parameters (weights, biases, etc) to {hyperparams['model_checkpoint']}")
            torch.save(model.state_dict(), hyperparams["model_checkpoint"])


def test(epoch, model, test_loader, device, hyperparams):
    """
    Test the neural network model.

    :param int epoch: number of the current training epoch
    :param model: PyTorch model to be trained
    :type: :py:class:`torch.nn.Module`
    :param test_loader: test loader providing all mini-batches
    :type test_loader: :py:class:`DataLoader`
    :param device: device to send the model and data to
    :type device: :py:class:`torch.device`
    :param hyperparams: training hyper-parameters
    :type: {str, str}
    """
    # Resend model to device including its new detector head
    model.to(device)
    # Set the module in evaluation mode
    model.eval()

    # NOTE: This is a custom metric using IoU (intersection over union); for
    # COCO or other more formal accuracy check the torchvision references
    def iou(obox, tbox):
        # Compute the area of the intersection
        intersect_x = max(0, min(obox[2], tbox[2]) - max(obox[0], tbox[0]))
        intersect_y = max(0, min(obox[3], tbox[3]) - max(obox[1], tbox[1]))
        # Area must be at least one pixel in exchange for a bit a precision
        intersect_area = (intersect_x + 1) * (intersect_y + 1)
        # Compute the area of both bounding boxes
        obox_area = (obox[2] - obox[0] + 1) * (obox[3] - obox[1] + 1)
        tbox_area = (tbox[2] - tbox[0] + 1) * (tbox[3] - tbox[1] + 1)
        return intersect_area / float(obox_area + tbox_area - intersect_area)
    def iou_per_sample(output, target):
        label_coeffs = numpy.asarray([[1 if o == t else 0 for o in output["labels"]]
                                                          for t in target["labels"]])
        score_coeffs = numpy.asarray([[s for s in output["scores"]]
                                         for _ in target["labels"]])
        box_ious = numpy.asarray([[iou(o, t) for o in output["boxes"]]
                                             for t in target["boxes"]])
        assert label_coeffs.shape == score_coeffs.shape == box_ious.shape
        proposal_scores = label_coeffs * score_coeffs * box_ious
        if min(proposal_scores.shape) == 0:
            return 0.0
        return numpy.average(numpy.max(proposal_scores, axis=1), axis=0)

    correct = 0
    with torch.no_grad():
        for images, targets in tqdm(test_loader):
            inputs = [image.to(device) for image in images]
            targets = [{k: v.cpu() for k, v in t.items()} for t in targets]

            outputs = model(inputs)
            outputs = [{k: v.cpu() for k, v in o.items()} for o in outputs]
            correct += sum(iou_per_sample(*sample) for sample in zip(outputs, targets))

    # Log the obtained measurements of accuracy
    logging.info(f"Test Epoch: {epoch}\tAccuracy: {correct:.2f}/{len(test_loader.dataset)}"
                 f" ({100 * correct / len(test_loader.dataset):.0f}%)")


# Set any hyperparameters
hyperparams = {}
hyperparams["epochs"] = 1
hyperparams["batch_size"] = 16
hyperparams["validation_split"] = 0.2
hyperparams["cpu_cores"] = multiprocessing.cpu_count()
hyperparams["log_interval"] = 10
hyperparams["save_interval"] = 100
hyperparams["learning_rate"] = 0.005
hyperparams["sgd_momentum"] = 0.9
hyperparams["weight_decay"] = 0.0005
hyperparams["step_size"] = 3
hyperparams["gamma"] = 0.1
hyperparams["dataset_source"] = "images/buttons"
hyperparams["model_checkpoint"] = "checkpoint.pth"


# Prepare all data
dataset = SyntheticDataset(path=hyperparams["dataset_source"],
                           transform=transforms.Compose([transforms.ToTensor()]))
logging.info(f"Loading complete synthetic dataset:\n{dataset.summary(train=True)}")
indices = torch.randperm(len(dataset)).tolist()
split_count = int(hyperparams["validation_split"] * len(dataset))
train_dataset = Subset(dataset, indices[split_count:])
test_dataset = Subset(dataset, indices[:split_count])
logging.info(f"Split into {len(train_dataset)} training samples and {len(test_dataset)} testing samples")
train_loader = torch.utils.data.DataLoader(train_dataset,
                                           batch_size=hyperparams["batch_size"],
                                           shuffle=True, num_workers=hyperparams["cpu_cores"],
                                           drop_last=True, collate_fn=lambda x: tuple(zip(*x)))
test_loader = torch.utils.data.DataLoader(test_dataset,
                                          batch_size=hyperparams["batch_size"],
                                          shuffle=False, num_workers=hyperparams["cpu_cores"],
                                          collate_fn=lambda x: tuple(zip(*x)))


# Initialize, configure, and synchronize the deep finder to get its backend model
finder = DeepFinder(synchronize=False)
# Use these CV parameters to configure the model
#finder.params["find"]["similarity"].value = 0.8
# have to set the number of classes if reusing a pretrained model (model param)
#finder.params["deep"]["classes"].value = len(dataset.classes)
#finder.params["deep"]["device"].value = "auto"
#finder.params["deep"]["arch"].value = "fasterrcnn_resnet50_fpn"
#finder.params["deep"]["model"].value = "checkpoint.pth"
# Synchronize at this stage to take into account all configuration
finder.synchronize()
# A bit awkward but the only current way to get the model's device
device = next(finder.net.parameters()).device
# Define custom class, backbone, or model parameters
if finder.params["deep"]["model"].value == "":
    # manually reinstantiate the model with a fully trainable backbone
    from torchvision.models.detection.backbone_utils import resnet_fpn_backbone
    # can change the backbone and its retained pre-training here
    backbone = resnet_fpn_backbone('resnet50', True, trainable_layers=3)
    if "faster" in finder.params["deep"]["arch"].value:
        from torchvision.models.detection.faster_rcnn import FasterRCNN
        finder.net = FasterRCNN(backbone, num_classes=len(dataset.classes))
    elif "mask" in finder.params["deep"]["arch"].value:
        from torchvision.models.detection.mask_rcnn import MaskRCNN
        finder.net = MaskRCNN(backbone, num_classes=len(dataset.classes))
    # TODO: eventually support keypoint R-CNN if it shows to be promising
    #elif "keypoint" in finder.params["deep"]["arch"].value:
    #    from torchvision.models.detection.keypoint_rcnn import KeypointRCNN
    #    finder.net = KeypointRCNN(backbone, num_classes=len(dataset.classes))
    else:
        raise ValueError(f'Invalid choice of architecture: {finder.params["deep"]["arch"].value}')
    finder.net.to(device)


# Train and test the network
for epoch in range(1, hyperparams["epochs"] + 1):
    train(epoch, finder.net, train_loader, device, hyperparams)
    test(epoch, finder.net, test_loader, device, hyperparams)


# Evaluate the trained network on a single test sample with image logging
NEEDLE = Pattern("1")
HAYSTACK = Image('some_buttons')
matches = finder.find(NEEDLE, HAYSTACK)


# Final cleanup steps
if REMOVE_LOGPATH:
    shutil.rmtree(LOGPATH)
GlobalConfig.image_logging_level = logging.ERROR
GlobalConfig.image_logging_destination = "./imglog"
GlobalConfig.image_logging_step_width = 3
