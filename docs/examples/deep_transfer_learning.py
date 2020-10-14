#!/usr/bin/python3

# Only needed if not installed system wide
import sys
sys.path.insert(0, '../..')


# Program start here
#
# Create a deep network capable of locating a given needle pattern.
# You will need to produce training and testing data as PyTorch tensors
# using the script provided in this project like for instance:
#
#     python misc/generate_pytorch_dataset.py --imglist "train.txt" --isize 150x150 --osize 15x15 --output train.pth
#     python misc/generate_pytorch_dataset.py --imglist "test.txt" --isize 150x150 --osize 15x15 --output test.pth
#
# to produce the data from a list of training or testing image paths and
# location coordinates which could be produced with OpenCV's cascade samples.
# The input and output size parameter have to match those of the configured
# network. This example demonstrated all following steps - network's training,
# testing, configuration, and reuse for a specific matching.

import logging
import shutil

from guibot.config import GlobalConfig
from guibot.imagelogger import ImageLogger
from guibot.fileresolver import FileResolver
from guibot.target import Pattern, Image
from guibot.finder import DeepFinder
from guibot.errors import *

import torch
import torch.optim as optim
import torch.nn.functional as F
from torch.utils.data import TensorDataset

# Parameters to toy with
file_resolver = FileResolver()
file_resolver.add_path('images/')
NEEDLE = Pattern(0)
HAYSTACK = Image('all_shapes')
LOGPATH = './tmp/'
REMOVE_LOGPATH = False
EPOCHS = 10


# Overall logging setup
handler = logging.StreamHandler()
logging.getLogger('').addHandler(handler)
logging.getLogger('').setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
GlobalConfig.image_logging_level = 0
GlobalConfig.image_logging_destination = LOGPATH
GlobalConfig.image_logging_step_width = 4
ImageLogger.step = 1


def train(model, hyperparams, train_samples, train_targets, epoch, data_filename=None):
    """
    Train the neural network model.

    :param str train_samples: filename for the samples dataset
    :param str train_targets: filename for the targets dataset
    :param int epoch: number of the current training epoch
    :param data_filename: file name for storing the trained model (won't store if None)
    :param data_filename: str or None
    """
    # create loader for the data (allowing batches and other extras)
    data_tensor, target_tensor = torch.load(train_samples), torch.load(train_targets)
    train_loader = torch.utils.data.DataLoader(TensorDataset(data_tensor, target_tensor),
                                               batch_size=hyperparams["batch_size"].value,
                                               shuffle=True, **kwargs)

    # initialize stochastic gradient descent optimizer for learning
    optimizer = optim.SGD(model.parameters(),
                          lr=hyperparams["learning_rate"],
                          momentum=hyperparams["sgd_momentum"])

    # set the module in training mode
    model.train()

    # loader iterator returns batches of samples
    for batch_idx, (data, target) in enumerate(train_loader):
        if hyperparams["use_cuda"]:
            data, target = data.cuda(), target.cuda()

        # main training step
        optimizer.zero_grad()
        output = model(data)
        loss = F.nll_loss(output, target)

        # backpropagation happens here
        loss.backward()
        # learning happens here
        optimizer.step()

        # log measurements on each ten batches
        if batch_idx % hyperparams["log_interval"] == 0:
            log.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                    epoch, batch_idx * len(data), len(train_loader.dataset),
                    100 * batch_idx / len(train_loader), loss.data[0]))

    # save the network state if required
    if data_filename is not None:
        state_dict = model.state_dict()
        log.debug("Resulting state dictionary (weights, biases, etc) of the network:\n%s", state_dict)
        torch.save(state_dict, data_filename)


def test(model, hyperparams, test_samples, test_targets):
    """
    Test the neural network model.

    :param str test_samples: filename for the samples dataset
    :param str test_targets: filename for the targets dataset
    """
    # create loader for the data (allowing batches and other extras)
    data_tensor, target_tensor = torch.load(test_samples), torch.load(test_targets)
    kwargs = {'num_workers': 1, 'pin_memory': True} if hyperparams["use_cuda"].value else {}
    test_loader = torch.utils.data.DataLoader(TensorDataset(data_tensor, target_tensor),
                                              batch_size=hyperparams["batch_size"].value,
                                              shuffle=True, **kwargs)

    # set the module in evaluation mode
    model.eval()

    test_loss = 0
    correct = 0
    with torch.no_grad():
        # loader iterator returns batches of samples
        for data, target in test_loader:
            if hyperparams["use_cuda"]:
                data, target = data.cuda(), target.cuda()

            # main testing step
            output = model(data)
            # accumulate negative log likelihood loss
            test_loss += F.nll_loss(output, target).data[0]
            # get the index of the max log-probability
            pred = output.data.max(1)[1]
            # calculate accuracy as well
            correct += pred.eq(target.data).cpu().sum()

    # loss function already averages over batch size
    test_loss /= len(test_loader)
    # log measurements - this is the only testing action
    log.info('Test set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)'.format(
            test_loss, correct, len(test_loader.dataset),
            100 * correct / len(test_loader.dataset)))


# Main configuration and training steps
finder = DeepFinder()
# use this to load pretrained model and train futher
#weights = torch.load(NEEDLE)
#finder.net.load_state_dict(weights)
# use this to configure
#finder.params["find"]["similarity"].value = 0.7
hyperparams = {}
hyperparams["batch_size"] = 1000
hyperparams["log_interval"] = 10
hyperparams["learning_rate"] = 0.01
hyperparams["sgd_momentum"] = 0.5
hyperparams["use_cuda"] = False
for epoch in range(1, EPOCHS + 1):
    # train for an epoch saving the obtained needle pattern once done
    train(finder.net, hyperparams, 'samples_train.pth', 'targets_train.pth', epoch, NEEDLE)
    # test trained network on test samples
    test(finder.net, hyperparams, 'samples_test.pth', 'targets_test.pth')


# Test trained network on a single test sample with image logging
NEEDLE.use_own_settings = True
settings = NEEDLE.match_settings
matches = finder.find(NEEDLE, HAYSTACK)


# Final cleanup steps
if REMOVE_LOGPATH:
    shutil.rmtree(LOGPATH)
GlobalConfig.image_logging_level = logging.ERROR
GlobalConfig.image_logging_destination = "./imglog"
GlobalConfig.image_logging_step_width = 3
