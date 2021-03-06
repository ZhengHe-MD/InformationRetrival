"""
Copyright 2015 University of Freiburg
Hannah Bast <bast@cs.uni-freiburg.de>
Evgeny Anatskiy <evgeny.anatskiy@jupiter.uni-freiburg.de>
Numair Mansur <numair.mansur@gmail.com>
"""

import re
import sys
import random
import logging
from math import log
from time import time

import numpy as np
from scipy.sparse import csr_matrix

logging.basicConfig(format='%(asctime)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class Kmeans:
    """ Class for a simple inverted index. """

    def __init__(self):
        self.inverted_lists = dict()
        self.record_lengths = dict()
        self.terms = []
        self.n = 0      # Total number of records (documents)
        self.m = 0      # Total number of terms
        self.A = None   # Term-document matrix

    def build_inverted_index(self, file_name):
        """
        Builds the inverted index from the given file.
        The format: one record per line.

        >>> ii = Kmeans()
        >>> ii.build_inverted_index('example.txt')
        >>> ii.terms
        ['internet', 'web', 'surfing', 'beach']
        >>> sorted(ii.inverted_lists.items())
        [('beach', {4: 1.0, 5: 1.0, 6: 1.0}), ('internet', {1: 1.0, 2: 1.0, \
4: 1.0}), ('surfing', {1: 0.2630344058337938, 2: 0.2630344058337938, \
3: 0.2630344058337938, 4: 0.334771061970283, 5: 0.2630344058337938}), \
('web', {1: 1.0, 3: 1.0, 4: 1.0})]
        """

        with open(file_name, 'r', encoding='utf-8') as file:
            doc_id = 0
            for line in file:
                doc_id += 1
                words = re.split('\W+', line)
                self.record_lengths[doc_id] = len(words)
                for term in words:
                    term = term.lower()
                    if any(term):
                        # If a word is seen for the first time, create an empty
                        # inverted list for it
                        if term not in self.inverted_lists:
                            self.terms.append(term)
                            self.inverted_lists[term] = dict()

                        if doc_id in self.inverted_lists[term].keys():
                            self.inverted_lists[term][doc_id] += 1
                        else:
                            self.inverted_lists[term][doc_id] = 1

            self.n = len(self.record_lengths)
            AVDL = sum(self.record_lengths.values()) / float(self.n)

            for term, inv_list in self.inverted_lists.items():
                for doc_id, tf in inv_list.items():
                    df = len(self.inverted_lists[term])
                    DL = self.record_lengths[doc_id]
                    self.inverted_lists[term][doc_id] = \
                        self.bm25_score(tf, df, self.n, AVDL, DL)

    def bm25_score(self, tf, df, N, AVDL, DL, bm25k=0.75, bm25b=0.0):
        return tf * (bm25k + 1) / (bm25k * (1 - bm25b + bm25b * DL / AVDL) +
                                   tf) * log((N / df), 2)

    def build_td_matrix(self, m=10000):
        """
        Computes the sparse term-document matrix using the (already built)
        inverted index.
        """
        terms = sorted(self.terms,
                       key=lambda t: len(self.inverted_lists[t]),
                       reverse=True)[:m]
        self.m = len(terms)

        start = time()
        nz_vals, row_inds, col_inds = [], [], []
        for i, term in enumerate(terms):
            for doc_id, score in self.inverted_lists[term].items():
                nz_vals.append(score)
                row_inds.append(i)
                col_inds.append(doc_id - 1)
        self.A = csr_matrix((nz_vals, (row_inds, col_inds)), dtype=float)
        print('Computation time: {0:.2f} s'.format(time() - start))

    def k_means(self, k=50):
        """
        Cluster into k cluster using k-means and return the k final centroids.
        """
        result = list()

        k = 2   # TEMPORARILY!

        self.norm_sp_row_l2(self.A.T)      # A matrix L2-normalization

        logger.info('Initializing centroids...')
        centroids = self.intitialize_centroids(k)   # Term-centroid matrix
        centroids = centroids.todense()
        self.norm_row_l2(centroids.T)       # Centroids matrix L2-normalization

        logger.info('Computing distances...')
        distances = self.compute_distances(centroids)
        self.norm_row_l2(distances.T)    # Distances matrix L2-normalization

        return result

    def intitialize_centroids(self, k):
        """
        Computes a m x k matrix with the initial (random) centroids.
        Note: All centroids must be different.
        """
        rows = sorted(random.sample(range(self.n), k))
        cols = [i for i in range(k)]
        vals = [1 for _ in range(k)]
        return self.A * csr_matrix((vals, (rows, cols)), shape=(self.n, k))

    def compute_distances(self, centroids):
        """
        Computes a k x n matrix such that the entry at i, j contains the
        distance between the i-th centroid and the j-th document.
        """
        # return centroids.T.dot(self.A)
        return 2 * (1 - centroids.T * self.A)

    def compute_assignment(self, distances):
        """
        Assigns to each document its closest centroid. Returns a k x n matrix
        such that the entry at i, j is 1 if document j is close to centroid i,
        and 0 otherwise.
        """
        pass

    def compute_centroids(self, docs, assignment):
        """
        Computes a m x k matrix with new centroids. Each centroid should be the
        average of all the documents assigned to it in the given assignment.
        """
        pass

    @staticmethod
    def norm_row_l2(matrix):
        """ L2 normalize rows of a dense matrix.
        >>> m = np.matrix([[1, 2], [2, 3]], dtype=float)
        >>> Kmeans.norm_row_l2(m)
        >>> m
        matrix([[ 0.4472136 ,  0.89442719],
                [ 0.5547002 ,  0.83205029]])
        """
        sq = np.multiply(matrix, matrix)
        row_sums = np.array(sq.sum(axis=1))[:, 0]
        row_sums = np.sqrt(row_sums)
        matrix /= row_sums[:, None]

    @staticmethod
    def norm_sp_row_l2(matrix):
        """ L2 normalize rows of a sparse csr_matrix.
        >>> m = np.matrix([[0, 1, 2], [0, 2, 3]], dtype=float)
        >>> m = csr_matrix(m)
        >>> Kmeans.norm_sp_row_l2(m)
        >>> m[0, 0]
        0.0
        >>> m[0, 1]
        0.44721359549995793
        >>> m[0, 2]
        0.89442719099991586
        >>> m[1, 0]
        0.0
        >>> m[1, 1]
        0.55470019622522915
        >>> m[1, 2]
        0.83205029433784372
        """
        sq = matrix.multiply(matrix)
        row_sums = np.array(sq.sum(axis=1))[:, 0]
        row_sums = np.sqrt(row_sums)
        row_indices, col_indices = matrix.nonzero()
        matrix.data /= row_sums[row_indices]

    @staticmethod
    def norm_sp_row_l1(matrix):
        """ L1 normalize rows of a dense matrix.
        >>> m = np.matrix([[1, 2], [3, 3]], dtype=float)
        >>> m = csr_matrix(m)
        >>> Kmeans.norm_sp_row_l1(m)
        >>> m.todense()
        matrix([[ 0.33333333,  0.66666667],
                [ 0.5       ,  0.5       ]])
        """
        row_sums = np.array(matrix.sum(axis=1))[:, 0]
        row_indices, col_indices = matrix.nonzero()
        matrix.data /= row_sums[row_indices]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Usage: python3 kmeans.py <records_file>')
        sys.exit()

    k = Kmeans()
    file_name = sys.argv[1]
    logger.info('Building inverted index "%s"...' % file_name)
    k.build_inverted_index(file_name)
    logger.info('Computing term-document matrix A...')
    k.build_td_matrix()
    result = k.k_means()
    print(result)
