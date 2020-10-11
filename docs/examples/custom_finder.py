import logging

from guibot.finder import DeepFinder
from guibot.errors import *


class CustomFinder(DeepFinder):
    """
    Custom matching backend with in-house CV algorithms.

    .. warning:: This matcher is currently not supported by our configuration.

    .. todo:: "in-house-raw" performs regular knn matching, but "in-house-region"
        performs a special filtering and replacement of matches based on
        positional information (it does not have ratio and symmetry tests
        and assumes that the needle is transformed preserving the relative
        positions of each pair of matches, i.e. no rotation is allowed,
        but scaling for example is supported)
    """

    def __init__(self, configure=True, synchronize=True):
        """Build a CV backend using custom matching."""
        super(CustomFinder, self).__init__(configure=False, synchronize=False)

        # additional preparation (no synchronization available)
        if configure:
            self.__configure_backend(reset=True)

    def __configure_backend(self, backend=None, category="custom", reset=False):
        if category != "custom":
            raise UnsupportedBackendError("Backend category '%s' is not supported" % category)
        if reset:
            super(CustomFinder, self).configure_backend("custom", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

        # TODO: these hyperparameters need to find their right place
        category = "deep"
        self.params[category]["batch_size"] = CVParameter(1000, 0, None)
        self.params[category]["log_interval"] = CVParameter(10, 1, None)
        self.params[category]["learning_rate"] = CVParameter(0.01, 0.0, 1.0)
        self.params[category]["sgd_momentum"] = CVParameter(0.5, 0.0, 1.0)

    def configure_backend(self, backend=None, category="custom", reset=False):
        """
        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def find(self, needle, haystack):
        """
        Custom implementation of the base method.

        See base method for details.

        .. todo:: This custom feature matching backend needs more serious reworking
                  before it even makes sense to get properly documented.
        """
        raise NotImplementedError("No custom matcher is currently implemented completely")

    def detect_features(self, needle, haystack):
        """
        In-house feature detection algorithm.

        :param needle: image to look for
        :type needle: :py:class:`target.Image`
        :param haystack: image to look in
        :type haystack: :py:class:`target.Image`

        .. warning:: This method is currently not fully implemented. The current
                     MSER might not be used in the actual implementation.
        """
        import cv2
        import numpy
        opencv_haystack = numpy.array(haystack.pil_image)
        opencv_needle = numpy.array(needle.pil_image)
        hgray = cv2.cvtColor(numpy.array(haystack.pil_image), cv2.COLOR_RGB2GRAY)
        ngray = cv2.cvtColor(numpy.array(needle.pil_image), cv2.COLOR_RGB2GRAY)

        # TODO: this MSER blob feature detector is also available in
        # version 2.2.3 - implement if necessary
        detector = cv2.MSER()
        hregions = detector.detect(hgray, None)
        nregions = detector.detect(ngray, None)
        hhulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in hregions]
        nhulls = [cv2.convexHull(p.reshape(-1, 1, 2)) for p in nregions]
        # show on final result
        cv2.polylines(opencv_haystack, hhulls, 1, (0, 255, 0))
        cv2.polylines(opencv_needle, nhulls, 1, (0, 255, 0))

    def regionMatch(self, desc1, desc2, kp1, kp2,
                    refinements=50, recalc_interval=10,
                    variants_k=100, variants_ratio=0.33):
        """
        Use location information to better decide on matched features.

        :param desc1: descriptors of the first image
        :param desc2: descriptors of the second image
        :param kp1: key points of the first image
        :param kp2: key points of the second image
        :param int refinements: number of points to relocate
        :param int recalc_interval: recalculation on a number of refinements
        :param int variants_k: kNN parameter for to limit the alternative variants of a badly positioned feature
        :param float variants_ratio: internal ratio test for knnMatch autostop (see below)
        :returns: obtained matches

        The knn distance is now only a heuristic for the search of best
        matched set as is information on relative location with regard
        to the other matches.

        .. todo:: handle a subset of matches (ignoring some matches if not all features are detected)
        .. todo:: disable kernel mapping (multiple needle feature mapped to a single haystack feature)
        """
        def ncoord(match):
            return kp1[match.queryIdx].pt

        def hcoord(match):
            return kp2[match.trainIdx].pt

        def rcoord(origin, target):
            # True is right/up or coinciding, False is left/down
            coord = [0, 0]
            if target[0] < origin[0]:
                coord[0] = -1
            elif target[0] > origin[0]:
                coord[0] = 1
            if target[1] < origin[1]:
                coord[1] = -1
            elif target[1] > origin[1]:
                coord[1] = 1
            log.log(9, "%s:%s=%s", origin, target, coord)
            return coord

        def compare_pos(match1, match2):
            hc = rcoord(hcoord(match1), hcoord(match2))
            nc = rcoord(ncoord(match1), ncoord(match2))

            valid_positioning = True
            if hc[0] != nc[0] and hc[0] != 0 and nc[0] != 0:
                valid_positioning = False
            if hc[1] != nc[1] and hc[1] != 0 and nc[1] != 0:
                valid_positioning = False

            log.log(9, "p1:p2 = %s in haystack and %s in needle", hc, nc)
            log.log(9, "is their relative positioning valid? %s", valid_positioning)

            return valid_positioning

        def match_cost(matches, new_match):
            if len(matches) == 0:
                return 0.0

            nominator = sum(float(not compare_pos(match, new_match)) for match in matches)
            denominator = float(len(matches))
            ratio = nominator / denominator
            log.log(9, "model <-> match = %i disagreeing / %i total matches",
                    nominator, denominator)

            # avoid 0 mapping, i.e. giving 0 positional
            # conflict to 0 distance matches or 0 distance
            # to matches with 0 positional conflict
            if ratio == 0.0 and new_match.distance != 0.0:
                ratio = 0.001
            elif new_match.distance == 0.0 and ratio != 0.0:
                new_match.distance = 0.001

            cost = ratio * new_match.distance
            log.log(9, "would be + %f cost", cost)
            log.log(9, "match reduction: %s",
                    cost / max(sum(m.distance for m in matches), 1))

            return cost

        results = self.knnMatch(desc1, desc2, variants_k,
                                1, variants_ratio)
        matches = [variants[0] for variants in results]
        ratings = [None for _ in matches]
        log.log(9, "%i matches in needle to start with", len(matches))

        # minimum one refinement is needed
        refinements = max(1, refinements)
        for i in range(refinements):

            # recalculate all ratings on some interval to save performance
            if i % recalc_interval == 0:
                for j in range(len(matches)):
                    # ratings forced to 0.0 cannot be improved
                    # because there are not better variants to use
                    if ratings[j] != 0.0:
                        ratings[j] = match_cost(matches, matches[j])
                quality = sum(ratings)
                log.debug("Recalculated quality: %s", quality)

                # nothing to improve if quality is perfect
                if quality == 0.0:
                    break

            outlier_index = ratings.index(max(ratings))
            outlier = matches[outlier_index]
            variants = results[outlier_index]
            log.log(9, "outlier m%i with rating %i", outlier_index, max(ratings))
            log.log(9, "%i match variants for needle match %i", len(variants), outlier_index)

            # add the match variant with a minimal cost
            variant_costs = []
            curr_cost_index = variants.index(outlier)
            for j, variant in enumerate(variants):

                # speed up using some heuristics
                if j > 0:
                    # cheap assertion paid for with the speedup
                    assert variants[j].queryIdx == variants[j - 1].queryIdx
                    if variants[j].trainIdx == variants[j - 1].trainIdx:
                        continue
                log.log(9, "variant %i is m%i/%i in n/h", j, variant.queryIdx, variant.trainIdx)
                log.log(9, "variant %i coord in n/h %s/%s", j, ncoord(variant), hcoord(variant))
                log.log(9, "variant distance: %s", variant.distance)

                matches[outlier_index] = variant
                variant_costs.append((j, match_cost(matches, variant)))

            min_cost_index, min_cost = min(variant_costs, key=lambda x: x[1])
            min_cost_variant = variants[min_cost_index]
            # if variant_costs.index(min(variant_costs)) != 0:
            log.log(9, "%s>%s i.e. variant %s", variant_costs, min_cost, min_cost_index)
            matches[outlier_index] = min_cost_variant
            ratings[outlier_index] = min_cost

            # when the best variant is the selected for improvement
            if min_cost_index == curr_cost_index:
                ratings[outlier_index] = 0.0

            # 0.0 is best quality
            log.debug("Overall quality: %s", sum(ratings))
            log.debug("Reduction: %s", sum(ratings) / max(sum(m.distance for m in matches), 1))

        return matches

    def knnMatch(self, desc1, desc2, k=1, desc4kp=1, autostop=0.0):
        """
        Performs k-Nearest Neighbor matching.

        :param desc1: descriptors of the first image
        :param desc2: descriptors of the second image
        :param int k: categorization up to k-th nearest neighbor
        :param int desc4kp: legacy parameter for the old SURF() feature detector where
                            desc4kp = len(desc2) / len(kp2) or analogically len(desc1) / len(kp1)
                            i.e. needle row 5 is a descriptor vector for needle keypoint 5
        :param float autostop: stop automatically if the ratio (dist to k)/(dist to k+1)
                               is close to 0, i.e. the k+1-th neighbor is too far.
        :returns: obtained matches
        """
        import cv2
        import numpy
        if desc4kp > 1:
            desc1 = numpy.array(desc1, dtype=numpy.float32).reshape((-1, desc4kp))
            desc2 = numpy.array(desc2, dtype=numpy.float32).reshape((-1, desc4kp))
            log.log(9, "%s %s", desc1.shape, desc2.shape)
        else:
            desc1 = numpy.array(desc1, dtype=numpy.float32)
            desc2 = numpy.array(desc2, dtype=numpy.float32)
        desc_size = desc2.shape[1]

        # kNN training - learn mapping from rows2 to kp2 index
        samples = desc2
        responses = numpy.arange(int(len(desc2) / desc4kp), dtype=numpy.float32)
        log.log(9, "%s %s", len(samples), len(responses))
        knn = cv2.KNearest()
        knn.train(samples, responses, maxK=k)

        matches = []
        # retrieve index and value through enumeration
        for i, descriptor in enumerate(desc1):
            descriptor = numpy.array(descriptor, dtype=numpy.float32).reshape((1, desc_size))
            log.log(9, "%s %s %s", i, descriptor.shape, samples[0].shape)
            kmatches = []

            for ki in range(k):
                _, res, _, dists = knn.find_nearest(descriptor, ki + 1)
                log.log(9, "%s %s %s", ki, res, dists)
                if len(dists[0]) > 1 and autostop > 0.0:

                    # TODO: perhaps ratio from first to last ki?
                    # smooth to make 0/0 case also defined as 1.0
                    dist1 = dists[0][-2] + 0.0000001
                    dist2 = dists[0][-1] + 0.0000001
                    ratio = dist1 / dist2
                    log.log(9, "%s %s", ratio, autostop)
                    if ratio < autostop:
                        break

                kmatches.append(cv2.DMatch(i, int(res[0][0]), dists[0][-1]))

            matches.append(tuple(kmatches))
        return matches

    def train(self, epochs, train_samples, train_targets, data_filename=None):
        """
        Train the convolutional neural network.

        :param int epochs: number of training epochs (train on all samples for each)
        :param str train_samples: filename for the samples dataset
        :param str train_targets: filename for the targets dataset
        :param data_filename: file name for storing the trained model (won't store if None)
        :param data_filename: str or None
        """
        # create loader for the data (allowing batches and other extras)
        import torch
        data_tensor, target_tensor = torch.load(train_samples), torch.load(train_targets)
        kwargs = {'num_workers': 1, 'pin_memory': True} if self.params["deep"]["use_cuda"].value else {}
        from torch.utils.data import TensorDataset
        train_loader = torch.utils.data.DataLoader(TensorDataset(data_tensor, target_tensor),
                                                   batch_size=self.params["deep"]["batch_size"].value,
                                                   shuffle=True, **kwargs)

        # initialize stochastic gradient descent optimizer for learning
        import torch.optim as optim
        optimizer = optim.SGD(self.net.parameters(),
                              lr=self.params["deep"]["learning_rate"].value,
                              momentum=self.params["deep"]["sgd_momentum"].value)

        # set the module in training mode
        self.net.train()

        import torch.nn.functional as F
        for epoch in range(1, epochs + 1):
            # loader iterator returns batches of samples
            for batch_idx, (data, target) in enumerate(train_loader):
                if self.params["deep"]["use_cuda"].value:
                    data, target = data.cuda(), target.cuda()

                # main training step
                optimizer.zero_grad()
                output = self.net(data)
                loss = F.nll_loss(output, target)

                # backpropagation happens here
                loss.backward()
                # learning happens here
                optimizer.step()

                # log measurements on each ten batches
                if batch_idx % self.params["deep"]["log_interval"].value == 0:
                    log.info('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                            epoch, batch_idx * len(data), len(train_loader.dataset),
                            100 * batch_idx / len(train_loader), loss.data[0]))

        # save the network state if required
        if data_filename is not None:
            state_dict = self.net.state_dict()
            log.debug("Resulting state dictionary (weights, biases, etc) of the network:\n%s", state_dict)
            torch.save(state_dict, data_filename)

    def test(self, train_samples, train_targets):
        """
        Test the convolutional neural network.

        :param str train_samples: filename for the samples dataset
        :param str train_targets: filename for the targets dataset
        """
        # create loader for the data (allowing batches and other extras)
        import torch
        data_tensor, target_tensor = torch.load(train_samples), torch.load(train_targets)
        kwargs = {'num_workers': 1, 'pin_memory': True} if self.params["deep"]["use_cuda"].value else {}
        from torch.utils.data import TensorDataset
        test_loader = torch.utils.data.DataLoader(TensorDataset(data_tensor, target_tensor),
                                                  batch_size=self.params["deep"]["batch_size"].value,
                                                  shuffle=True, **kwargs)

        # set the module in evaluation mode
        self.net.eval()

        test_loss = 0
        correct = 0
        import torch.nn.functional as F
        with torch.no_grad():
            # loader iterator returns batches of samples
            for data, target in test_loader:
                if self.params["deep"]["use_cuda"].value:
                    data, target = data.cuda(), target.cuda()

                # main testing step
                output = self.net(data)
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
