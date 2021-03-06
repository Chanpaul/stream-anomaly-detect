# coding: utf-8

"""
Implementation of algorithms proposed by:

    H. Huang and S. Kasiviswanathan, "Streaming Anomaly Detection Using Randomized Matrix Sketching," http://bit.ly/1FaDw6S.
"""

import numpy as np
import numpy.linalg as ln

class AnomDetect:
    def __init__(self, Y0, criterion='p', criterion_v=0.5, ell=0):
        """
        :param Y0: m-by-n training matrix (n non-anomaly samples)
        :param criterion: 'p' or 'th' to choose how to split sorted samples between anomaly and non-anomaly
        :param criterion_v: criterion value; 'p': percentage of anomalies, 'th': threshold of the anomaly score
        :param ell: sketch size for a sketched m-by-ell matrix
        """

        self.criterion = criterion
        self.criterion_v = criterion_v

        # number of features
        self.m = Y0.shape[0]

        # if ell is not specified, it will be set square-root of m (number of features)
        if ell < 1: self.ell = int(np.sqrt(self.m))
        else: self.ell = ell

        # initial k orthogonal bases are computed by truncated SVD
        U, s, V = ln.svd(Y0, full_matrices=False)
        self.U = U[:, :self.ell]
        s = s[:self.ell]

        # shrink step in Frequent Directions algorithm
        # (shrink singular values based on the squared smallest singular value)
        delta = s[-1] ** 2
        s = np.sqrt(s ** 2 - delta)

        # define initial sketched matrix B
        self.B = np.dot(self.U, np.diag(s))

    def detect(self, Y):
        """
        Alg. 1: Prototype algorithm for detecting anomalies at time t
        :param Y: m-by-n_t new observance matrix at time t
        :return: two arrays of non-anomaly indices and anomaly indices
        """

        # [Step 1] Anomaly score construction step
        n = Y.shape[1]
        scores = np.array([])

        # for each input vector
        for i in range(n):
            y = Y[:, i]

            # solve the least-square problem
            x = np.dot(self.U.T, y)

            # compute anomaly score
            a = ln.norm(np.dot(np.identity(self.m) - np.dot(self.U, self.U.T), y), ord=2)
            scores = np.append(scores, a)

        # get both of anomaly/non-anomaly indices
        if self.criterion == 'p':
            p = self.criterion_v
            # top p% high-scored samples will be anomalies
            sorted_idx = np.argsort(scores)[::-1] # descending order
            n_anomaly = int(n * p)
            anomaly_idx = sorted_idx[:n_anomaly]
            non_anomaly_idx = sorted_idx[n_anomaly:]
        elif self.criterion == 'th':
            th = self.criterion_v
            # thresholding the anomaly score
            anomaly_idx = np.where(scores > th)[0]
            non_anomaly_idx = np.where(scores <= th)[0]

        # [Step 2] Updating the singular vectors
        self.sketch_update(Y[:, non_anomaly_idx])

        return anomaly_idx, non_anomaly_idx

    def sketch_update(self, Y):
        """
        Alg. 4: Streaming update of the singular vectors at time t
        :param Y: m-by-n_t "good" matrix which has n_t non-anomaly samples
        """

        n = Y.shape[1]

        # combine current sketched matrix with input at time t
        # D: m-by-(n+ell) matrix
        D = np.hstack((self.B, Y))

        U, s, V = ln.svd(D, full_matrices=False)

        # update k orthogonal bases
        self.U =  U[:, :self.ell]
        s = s[:self.ell]

        # shrink step in Frequent Directions algorithm
        # (shrink singular values based on the squared smallest singular value)
        delta = s[-1] ** 2
        s = np.sqrt(s ** 2 - delta)

        # update sketched matrix B
        # (focus on column singular vectors)
        self.B = np.dot(self.U, np.diag(s))
