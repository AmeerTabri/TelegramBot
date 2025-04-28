from pathlib import Path
import random

from matplotlib.image import imread, imsave


def rgb2gray(rgb):
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    gray = 0.2989 * r + 0.5870 * g + 0.1140 * b
    return gray


class Img:

    def __init__(self, path):
        """
        Do not change the constructor implementation
        """
        self.path = Path(path)
        self.data = rgb2gray(imread(path)).tolist()

    def save_img(self):
        """
        Do not change the below implementation
        """
        new_path = self.path.with_name(self.path.stem + '_filtered' + self.path.suffix)
        imsave(new_path, self.data, cmap='gray')
        return new_path

    def blur(self, blur_level=16):

        height = len(self.data)
        width = len(self.data[0])
        filter_sum = blur_level ** 2

        result = []
        for i in range(height - blur_level + 1):
            row_result = []
            for j in range(width - blur_level + 1):
                sub_matrix = [row[j:j + blur_level] for row in self.data[i:i + blur_level]]
                average = sum(sum(sub_row) for sub_row in sub_matrix) // filter_sum
                row_result.append(average)
            result.append(row_result)

        self.data = result

    def contour(self):
        for i, row in enumerate(self.data):
            res = []
            for j in range(1, len(row)):
                res.append(abs(row[j-1] - row[j]))

            self.data[i] = res

    def rotate(self):
        n, m = len(self.data), len(self.data[0])
        rotated = [[0] * n for _ in range(m)]

        for i in range(n):
            for j in range(m):
                rotated[j][n - 1 - i] = self.data[i][j]

        self.data = rotated

    def salt_n_pepper(self):
        n, m = len(self.data), len(self.data[0])
        for i in range(n):
            for j in range(m):
                rand = random.random()
                if rand < 0.2:
                    self.data[i][j] = 255
                elif rand > 0.8:
                    self.data[i][j] = 0

    def concat(self, other_img, direction='horizontal'):
        n1, m1 = len(self.data), len(self.data[0])
        n2, m2 = len(other_img.data), len(other_img.data[0])

        if direction == 'horizontal':
            if n1 != n2:
                raise RuntimeError()
            concat_image = [[0] * (m1 + m2) for _ in range(n1)]
            for i in range(n1):
                for j in range(m1 + m2):
                    concat_image[i][j] = self.data[i][j] if j < m1 else other_img.data[i][j - m1]
            self.data = concat_image

        elif direction == 'vertical':
            if m1 != m2:
                raise RuntimeError()
            concat_image = [[0] * m1 for _ in range(n1+n2)]
            for i in range(n1 + n2):
                for j in range(m1):
                    concat_image[i][j] = self.data[i][j] if i < n1 else other_img.data[i - n1][j]
            self.data = concat_image

    def segment(self):
        n, m = len(self.data), len(self.data[0])
        for i in range(n):
            for j in range(m):
                if self.data[i][j] > 100:
                    self.data[i][j] = 255
                else:
                    self.data[i][j] = 0

    def invert(self):
        n, m = len(self.data), len(self.data[0])
        for i in range(n):
            for j in range(m):
                self.data[i][j] = 255 - self.data[i][j]

    def binary(self):
        n, m = len(self.data), len(self.data[0])
        for i in range(n):
            for j in range(m):
                if self.data[i][j] > 127:
                    self.data[i][j] = 255
                else:
                    self.data[i][j] = 0

    def flip(self, direction='vertical'):
        n, m = len(self.data), len(self.data[0])

        if direction == 'horizontal':
            for i in range(n // 2):
                for j in range(m):
                    self.data[i][j], self.data[n - i - 1][j] = self.data[n - i - 1][j], self.data[i][j]

        elif direction == 'vertical':
            for i in range(n):
                for j in range(m // 2):
                    self.data[i][j], self.data[i][m - j - 1] = self.data[i][m - j - 1], self.data[i][j]

    # def apply_kernel(self, kernel, factor=1):
    #     k_size = len(kernel)
    #     offset = k_size // 2
    #     n, m = len(self.data), len(self.data[0])
    #
    #     result = [[0] * m for _ in range(n)]
    #
    #     for i in range(offset, n - offset):
    #         for j in range(offset, m - offset):
    #             acc = 0
    #             for ki in range(k_size):
    #                 for kj in range(k_size):
    #                     ni = i + ki - offset
    #                     nj = j + kj - offset
    #                     acc += self.data[ni][nj] * kernel[ki][kj]
    #             result[i][j] = min(max(acc // factor, 0), 255)  # Clamp to 0-255
    #
    #     self.data = result
