from pathlib import Path
import random
import requests
import boto3
import json
import os

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
        n, m = len(self.data), len(self.data[0])
        if blur_level <= 0 or blur_level >= min(n, m):
            raise RuntimeError(f"Invalid blur level!")
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
                raise RuntimeError("Cannot concatenate horizontally: image heights are different.")
            concat_image = [[0] * (m1 + m2) for _ in range(n1)]
            for i in range(n1):
                for j in range(m1 + m2):
                    concat_image[i][j] = self.data[i][j] if j < m1 else other_img.data[i][j - m1]
            self.data = concat_image

        elif direction == 'vertical':
            if m1 != m2:
                raise RuntimeError("Cannot concatenate vertically: image widths are different.")
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

        if direction == 'vertical':
            for i in range(n):
                for j in range(m // 2):
                    self.data[i][j], self.data[i][m - j - 1] = self.data[i][m - j - 1], self.data[i][j]

        elif direction == 'horizontal':
            for i in range(n // 2):
                for j in range(m):
                    self.data[i][j], self.data[n - i - 1][j] = self.data[n - i - 1][j], self.data[i][j]

    def pixelate(self, pixelate_level=10):
        n, m = len(self.data), len(self.data[0])
        if pixelate_level <= 0 or pixelate_level >= min(n, m):
            raise RuntimeError(f"Invalid pixelation level!")
        for i in range(0, n, pixelate_level):
            for j in range(0, m, pixelate_level):
                block = [self.data[x][y] for x in range(i, min(i + pixelate_level, n)) for y in range(j, min(j + pixelate_level, m))]
                avg = sum(block) // len(block)
                for x in range(i, min(i + pixelate_level, n)):
                    for y in range(j, min(j + pixelate_level, m)):
                        self.data[x][y] = avg

    def predict(self, chat_id):
        print("👉 predict() called with chat_id:", chat_id)

        queue_url = os.getenv('QUEUE_URL')
        aws_region = os.getenv('SQS_AWS_REGION')
        sqs = boto3.client('sqs', region_name=aws_region)

        message = {
            "image_name": self.path.name,
            "chat_id": str(chat_id)
        }

        try:
            response = sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
            print("✅ Message sent to SQS:", response['MessageId'])
            return {"status": "queued", "message_id": response['MessageId']}
        except Exception as e:
            print("❌ Failed to send message to SQS:", e)
            return {"status": "error", "error": str(e)}
