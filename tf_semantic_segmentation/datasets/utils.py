from ..utils import get_files, download_from_google_drive, download_and_extract

import random
import imageio
import collections
import tensorflow as tf
import numpy as np
import multiprocessing

Color = collections.namedtuple('Color', ['r', 'g', 'b'])

# save google drive records here for now
google_drive_records_by_tag = {
    'pascal-512x512-rgb-crop-and-pad': "1gtmElm8jOWqdFDt_StZXYudJOwFYQKyU",
    'tacobinary-512x512-resize': "1ziK05B29YjTpx6UuawHQ_oantvMoiqPi"
}


class DataType:
    TRAIN, TEST, VAL = 'train', 'test', 'val'

    @staticmethod
    def get():
        return list(map(lambda x: DataType.__dict__[x], list(filter(lambda k: not k.startswith("__") and type(DataType.__dict__[k]) == str, DataType.__dict__))))


def get_train_test_val_from_list(l, train_split=0.8, val_split=0.5, shuffle=True, rand=lambda: 0.2):
    if shuffle:
        random.shuffle(l, random=rand)

    trainset = l[:int(round(train_split * len(l)))]
    valtestset = l[int(round(train_split * len(l))):]
    testset = valtestset[int(round(val_split * len(valtestset))):]
    valset = valtestset[:int(round(val_split * len(valtestset)))]
    return trainset, testset, valset


def get_split(l, train_split=0.8, val_split=0.5, shuffle=True, rand=lambda: 0.2):
    trainset, testset, valset = get_train_test_val_from_list(
        l, train_split=train_split, val_split=val_split, shuffle=shuffle, rand=rand)
    return {
        DataType.TRAIN: trainset,
        DataType.VAL: valset,
        DataType.TEST: testset
    }


def get_split_from_list(l, split=0.9):
    trainset = l[:int(round(split * len(l)))]
    valset = l[int(round(split * len(l))):]
    return trainset, valset


def get_split_from_dirs(images_dir, labels_dir, extensions=['png'], train_split=0.8, val_split=0.5, shuffle=True, rand=lambda: 0.2):
    images = get_files(images_dir, extensions=extensions)
    labels = get_files(labels_dir, extensions=extensions)

    trainset = list(zip(images, labels))
    return get_split(trainset, train_split=train_split, val_split=val_split, shuffle=shuffle, rand=rand)


def image_generator(data, color_map=None):
    import numpy as np

    def gen():
        for image_path, label_path in data:
            labels = imageio.imread(label_path)[:, :, :3]
            labels_idx = np.array(labels.shape, np.uint8)
            for color, value in color_map.items():
                labels_idx[labels == np.asarray(
                    [color.r, color.g, color.b])] = [value, value, value]
            labels_idx = labels_idx.mean(axis=-1)
            # print(labels_idx.max(), labels_idx.min())
            yield imageio.imread(image_path), labels_idx
    return gen


def convert2tfdataset(dataset, data_type, randomize=True):

    def gen():
        indexes = np.arange(dataset.num_examples(data_type))
        if randomize:
            indexes = np.random.permutation(indexes)

        data = dataset.raw()[data_type]
        for idx in indexes:
            example = data[idx]
            image, mask = dataset.parse_example(example)

            shape = image.shape

            if len(shape) == 2:
                shape = [shape[0], shape[1], 1]

            if len(image.shape) == 2:
                image = np.expand_dims(image, axis=-1)

            yield image, mask, dataset.num_classes, shape

    def map_fn(image, labels, num_classes, shape):
        image = tf.reshape(image, shape)
        labels = tf.reshape(labels, (shape[0], shape[1]))
        return image, labels, num_classes

    ds = tf.data.Dataset.from_generator(
        gen, (tf.uint8, tf.uint8, tf.int64, tf.int64), ([None, None, None], [None, None], [], [3]))
    ds = ds.map(map_fn, num_parallel_calls=multiprocessing.cpu_count())

    #ds[0] = tf.reshape(ds[0], ds[2])
    #ds[1] = tf.reshape(ds[1], [ds[2][0], ds[2][1], tf.convert_to_tensor(dataset.num_classes, tf.int64)])
    return ds


def download_records(tag, destitnation_dir):
    if tag in google_drive_records_by_tag:
        drive_id = google_drive_records_by_tag[tag]
        print("download and extract ", drive_id, tag, destitnation_dir)
        download_and_extract(('%s.zip' % tag, drive_id), destitnation_dir, chk_exists=False)
    else:
        raise Exception("cannot download records of tag %s, please use one of %s" % (tag, str(google_drive_records_by_tag.keys())))