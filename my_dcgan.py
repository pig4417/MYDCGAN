# -*- coding: utf-8 -*-
"""MY_DCGAN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1JJvvl-6rYEf9way-aIHttGSDO1PmGU7R

# **硬體資源確認:**
"""

gpu_info = !nvidia-smi
gpu_info = '\n'.join(gpu_info)
if gpu_info.find('failed') >= 0:
  print('Not connected to a GPU')
else:
  print(gpu_info)

from psutil import virtual_memory
ram_gb = virtual_memory().total / 1e9
print('Your runtime has {:.1f} gigabytes of available RAM\n'.format(ram_gb))

if ram_gb < 20:
  print('Not using a high-RAM runtime')
else:
  print('You are using a high-RAM runtime!')

import tensorflow as tf
import os
import numpy as np
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras import optimizers
from tqdm import tqdm
import time
import matplotlib.pyplot as plt
import gdown
import zipfile

"""# **Preprocessing:**"""

# 直接下載celeba資料集使用(Google colab)
if not os.path.isdir("/content/dataset"):
  os.makedirs("/content/dataset")                        # 不要載到drive 直接放雲端本機

# url = "https://drive.google.com/uc?id=1O7m1010EJjLE5QxLZiM9Fpjs7Oj6e684"  #Celeba
url = "https://drive.google.com/u/0/uc?id=1GTiaKUgKWzNAWzQ00sYvmb8GELKk8bsN&export=download" #FFHQ
output = "dataset/data.zip"
gdown.download(url, output, quiet=False)

with zipfile.ZipFile("dataset/data.zip", "r") as zipobj:
    zipobj.extractall("dataset")

# FFHQ
path = "/content/dataset/thumbnails128x128"
for i in range(112):
  fname = "{0:05d}.png".format(i + 1)
  os.remove(os.path.join(path, fname))

# 資料集預處理
# PATH = "/content/drive/MyDrive/Colab Notebooks/celeba" # for test
PATH = "/content/dataset" # for train
dataset = keras.preprocessing.image_dataset_from_directory(
    PATH, label_mode=None, color_mode='rgb', image_size=(128, 128), batch_size=256, shuffle=True
)

# dataset = dataset.batch(1, drop_remainder=True)
dataset = dataset.map(lambda x: x / 255.0)       # ※normalize [0,1]
dataset = dataset.map(lambda x: (x - 127.5)/ 127.5)  # ※normalize [-1,1]

# 預先讀取訓練資料，提升效能
dataset = dataset.prefetch(buffer_size=256)

"""# **Generator:**"""

# 建構生成器
def build_generator(latent_dim=128):
    # 輸入潛在空間中向量
    vector_input = layers.Input(shape=(latent_dim,), name='G_input')

    x = layers.Dense(1024 * 8 * 8, use_bias=False, name='G1')(vector_input)
    # x = layers.BatchNormalization(epsilon=0.001, name='G1_bn')(x)           # Reshape no BN !
    # (None, 1024)
    x = layers.Reshape((8, 8, 1024), name='G_reshape')(x)
    x = layers.LeakyReLU(alpha=0.2, name='G1_Lrelu')(x)
    # (None, 1, 1, 1024)

    x = layers.Conv2DTranspose(1024, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G2')(x)
    x = layers.BatchNormalization(epsilon=0.001, name='G2_bn')(x)
    x = layers.LeakyReLU(alpha=0.2, name='G2_Lrelu')(x)
    # (None, 4, 4, 1024)

    '''
    ......
    '''
    x = layers.Conv2DTranspose(512, kernel_size=4,  strides=2, padding='same', use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.LeakyReLU(alpha=0.2)(x)
    # (None, 16, 16, 512)

    x = layers.Conv2DTranspose(256, kernel_size=4,  strides=2, padding='same', use_bias=False)(x)
    x = layers.BatchNormalization()(x)
    x = layers.LeakyReLU(alpha=0.2)(x)
    # (None, 32, 32, 256) 

    x = layers.Conv2DTranspose(128, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G5')(x)
    x = layers.BatchNormalization(epsilon=0.001, name='G5_bn')(x)
    x = layers.LeakyReLU(alpha=0.2, name='G5_Lrelu')(x)
    # (None, 32, 32, 128)

    x = layers.Conv2DTranspose(64, kernel_size=(4, 4),  strides=(1, 1), padding='same', use_bias=False, name='G6')(x)
    x = layers.BatchNormalization(epsilon=0.001, name='G6_bn')(x)
    x = layers.LeakyReLU(alpha=0.2, name='G6_Lrelu')(x)
    # (None, 64, 64, 64)

    x = layers.Conv2DTranspose(3, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G7')(x)
    img = layers.Activation('tanh', name='G_final')(x)
    # (None, 128, 128, 3) 
    generator = models.Model(vector_input, img, name='Generator')

    generator.summary()
    return generator

G = build_generator(latent_dim=128)

"""### 1024 128x128x3"""

# # 建構生成器
# def build_generator(latent_dim=128):
#     # 輸入潛在空間中向量
#     vector_input = layers.Input(shape=(latent_dim,), name='G_input')

#     x = layers.Dense(1024 * 8 * 8, use_bias=False, name='G_1')(vector_input)
#     x = layers.ReLU(name='G_relu1')(x)
#     # (None, 32768)
#     x = layers.Reshape((8, 8, 1024), name='G_reshape')(x)
    
#     # (None, 8, 8, 512)
#     x = layers.Conv2DTranspose(512, kernel_size=(4, 4),  strides=(1, 1), padding='same', use_bias=False, name='G_2')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='G_bn2')(x)
#     x = layers.ReLU(name='G_relu2')(x) 
#     # -------------------------
#     # transposedConv 棋盤偽影
#     # kernel_size & strides
#     # -------------------------
#     x = layers.Conv2DTranspose(256, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G_3')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='G_bn3')(x)
#     x = layers.ReLU(name='G_relu3')(x)        # LeakyReLU(inplace=True)
#     # ReLU in G
#     # (None, 16, 16, 256) 

#     x = layers.Conv2DTranspose(128, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G_4')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='G_bn4')(x)
#     x = layers.ReLU(name='G_relu4')(x)
#     # (None, 32, 32, 128)

#     x = layers.Conv2DTranspose(64, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G_5')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='G_bn5')(x)
#     x = layers.ReLU(name='G_relu5')(x)
#     # (None, 64, 64, 64)

#     x = layers.Conv2DTranspose(3, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G_6')(x)
#     img = layers.Activation('tanh', name='G_final')(x)      # Wyh TANH ?????
#     # 因輸入向量來自常態分布(高斯)
#     # (None, 64, 64, 3) 
#     generator = models.Model(vector_input, img, name='Generator')

#     generator.summary()
#     return generator

# G = build_generator(latent_dim=128)

"""512 64x64x3"""

# # 建構生成器
# def build_generator(latent_dim=128):
#     # 輸入潛在空間中向量
#     vector_input = layers.Input(shape=(latent_dim,), name='G_input')
#     # -------------------------
#     #    use_bias=False
#     #  通過禁用bias加速訓練
#     #因為輸出normalize後bias可忽略
#     # -------------------------
#     x = layers.Dense(512 * 8 * 8, use_bias=False, name='G_1')(vector_input)
#     x = layers.BatchNormalization(epsilon=0.001, name='G_bn1')(x)
#     x = layers.ReLU(name='G_relu1')(x)
#     # (None, 32768)
#     x = layers.Reshape((8, 8, 512), name='G_reshape')(x)
#     # (None, 8, 8, 512)

#     # -------------------------
#     # transposedConv 棋盤偽影
#     # kernel_size & strides
#     # -------------------------
#     x = layers.Conv2DTranspose(256, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G_2')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='G_bn2')(x)
#     x = layers.ReLU(name='G_relu2')(x)        # LeakyReLU(inplace=True)
#     # ReLU in G
#     # (None, 16, 16, 256) 

#     x = layers.Conv2DTranspose(128, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G_3')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='G_bn3')(x)
#     x = layers.ReLU(name='G_relu3')(x)
#     # (None, 32, 32, 128)

#     x = layers.Conv2DTranspose(64, kernel_size=(4, 4),  strides=(2, 2), padding='same', use_bias=False, name='G_4')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='G_bn4')(x)
#     x = layers.ReLU(name='G_relu4')(x)
#     # (None, 64, 64, 64)

#     x = layers.Conv2DTranspose(3, kernel_size=(4, 4),  strides=(1, 1), padding='same', use_bias=False, name='G_5')(x) # 測試
#     # x = layers.Conv2D(3, kernel_size=(5, 5), padding='same', use_bias=False, name='G_5')(x)
#     img = layers.Activation('tanh', name='G_final')(x)      # Wyh TANH ?????
#     # 因輸入向量來自常態分布(高斯)
#     # (None, 64, 64, 3) 
#     generator = models.Model(vector_input, img, name='Generator')

#     generator.summary()
#     return generator

# G = build_generator(latent_dim=128)

"""# **Discriminator:**

```
# All Conv block with dropout
```
"""

# 建構鑑別器 (WGAN)
def build_discriminator(img_shape):  
    input_img = layers.Input(shape=img_shape, name='D_input')

    x = layers.Conv2D(64, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D1')(input_img)
    x = layers.BatchNormalization(epsilon=0.001, name='D1_bn')(x)
    x = layers.LeakyReLU(alpha=0.2, name='D1_Lrelu')(x)
    x = layers.Dropout(0.3, name='D1_drop')(x)
    # (None, 64, 64, 64)

    x = layers.Conv2D(128, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D2')(x)
    x = layers.BatchNormalization(epsilon=0.001, name='D2_bn')(x)
    x = layers.LeakyReLU(alpha=0.2, name='D2_Lrelu')(x)
    x = layers.Dropout(0.3, name='D2_drop')(x)
    # (None, 32, 32, 128)

    x = layers.Conv2D(256, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D3')(x)
    x = layers.BatchNormalization(epsilon=0.001, name='D3_bn')(x)
    x = layers.LeakyReLU(alpha=0.2, name='D3_Lrelu')(x)
    x = layers.Dropout(0.3, name='D3_drop')(x)
    # (None, 16, 16, 256)

    x = layers.Conv2D(512, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D4')(x)
    x = layers.BatchNormalization(epsilon=0.001, name='D4_bn')(x)
    x = layers.LeakyReLU(alpha=0.2, name='D4_Lrelu')(x)
    x = layers.Dropout(0.3, name='D4_drop')(x)
    # (None, 8, 8, 512)

    x = layers.Conv2D(1024, kernel_size=(4, 4), strides=(1, 1), padding='same', use_bias=False, name='D5')(x)
    x = layers.BatchNormalization(epsilon=0.001, name='D5_bn')(x)
    x = layers.LeakyReLU(alpha=0.2, name='D5_Lrelu')(x)
    x = layers.Dropout(0.3, name='D5_drop')(x)
    # (None, 4, 4, 1024)

    x = layers.Flatten(name='D_flat')(x)
    # (None, 16384)

    out = layers.Dense(1, use_bias=False, name='D_5')(x)
    # out = layers.Activation('sigmoid', name='D_final')(x)           # WGAN不使用sigmoid作為D輸出
    # (None, 1)                                  # 此時輸出不再為可能為真的"機率"而是為真的"程度" 
    discriminator = models.Model(input_img, out, name='Discriminator')

    discriminator.summary()
    return discriminator

# D = build_discriminator((128, 128, 3))

# # 建構鑑別器
# def build_discriminator(img_shape):  
#     input_img = layers.Input(shape=img_shape, name='D_input')

#     x = layers.Conv2D(64, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D1')(input_img)
#     x = layers.BatchNormalization(epsilon=0.001, name='D1_bn')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D1_Lrelu')(x)
#     # (None, 64, 64, 64)

#     x = layers.Conv2D(128, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D2')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D2_bn')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D2_Lrelu')(x)
#     # (None, 32, 32, 128)

#     x = layers.Conv2D(256, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D3')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D3_bn')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D3_Lrelu')(x)
#     # (None, 16, 16, 256)

#     x = layers.Conv2D(512, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D4')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D4_bn')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D4_Lrelu')(x)
#     # (None, 8, 8, 512)

#     x = layers.Conv2D(1024, kernel_size=(4, 4), strides=(1, 1), padding='same', use_bias=False, name='D5')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D5_bn')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D5_Lrelu')(x)
#     # (None, 4, 4, 1024)

#     x = layers.Dropout(0.5, name='D_drop1')(x)
#     x = layers.Flatten(name='D_flat')(x)
#     # (None, 16384)
#     x = layers.Dropout(0.5, name='D_drop2')(x)

#     x = layers.Dense(1, use_bias=False, name='D_5')(x)
#     out = layers.Activation('sigmoid', name='D_final')(x)
#     # (None, 1)
#     discriminator = models.Model(input_img, out, name='Discriminator')

#     discriminator.summary()
#     return discriminator

# D = build_discriminator((128, 128, 3))

"""1024 更多dropout應對mode collapse?"""

# # 建構鑑別器
# def build_discriminator(img_shape):  
#     input_img = layers.Input(shape=img_shape, name='D_input')

#     x = layers.Conv2D(64, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D_1')(input_img)
#     x = layers.BatchNormalization(epsilon=0.001, name='D_bn1')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D_Lrelu1')(x)
#     # (None, 32, 32, 64)

#     x = layers.Conv2D(128, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D_2')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D_bn2')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D_Lrelu2')(x)
#     # (None, 16, 16, 128)

#     x = layers.Conv2D(256, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D_3')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D_bn3')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D_Lrelu3')(x)
#     # (None, 8, 8, 256)

#     x = layers.Conv2D(512, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D_4')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D_bn4')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D_Lrelu4')(x)
#     # (None, 4, 4, 512)

#     # x = layers.Conv2D(1024, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D_5')(x)
#     # x = layers.BatchNormalization(epsilon=0.001, name='D_bn5')(x)
#     # x = layers.LeakyReLU(alpha=0.2, name='D_Lrelu5')(x)

#     x = layers.Dropout(0.5, name='D_drop1')(x)
#     x = layers.Flatten(name='D_flat')(x)
#     # 使用Dropout引入隨機性，幫助訓練
#     x = layers.Dropout(0.5, name='D_drop2')(x)
#     # (None, 8192)

#     x = layers.Dense(1, use_bias=False, name='D_5')(x)
#     out = layers.Activation('sigmoid', name='D_final')(x)
#     # (None, 1)
#     discriminator = models.Model(input_img, out, name='Discriminator')

#     discriminator.summary()
#     return discriminator

# D = build_discriminator((128, 128, 3))

"""512"""

# # 建構鑑別器
# def build_discriminator(img_shape):  
#     input_img = layers.Input(shape=img_shape, name='D_input')

#     x = layers.Conv2D(64, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D_1')(input_img)
#     x = layers.BatchNormalization(epsilon=0.001, name='D_bn1')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D_Lrelu1')(x)
#     # (None, 32, 32, 64)

#     x = layers.Conv2D(128, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D_2')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D_bn2')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D_Lrelu2')(x)
#     # (None, 16, 16, 128)

#     x = layers.Conv2D(256, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D_3')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D_bn3')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D_Lrelu3')(x)
#     # (None, 8, 8, 256)

#     x = layers.Conv2D(512, kernel_size=(4, 4), strides=(2, 2), padding='same', use_bias=False, name='D_4')(x)
#     x = layers.BatchNormalization(epsilon=0.001, name='D_bn4')(x)
#     x = layers.LeakyReLU(alpha=0.2, name='D_Lrelu4')(x)
#     # (None, 4, 4, 512)

#     x = layers.Dropout(0.5, name='D_drop1')(x)
#     x = layers.Flatten(name='D_flat')(x)
#     # 使用Dropout引入隨機性，幫助訓練
#     x = layers.Dropout(0.5, name='D_drop2')(x)
#     # (None, 8192)

#     x = layers.Dense(1, use_bias=False, name='D_5')(x)
#     out = layers.Activation('sigmoid', name='D_final')(x)
#     # (None, 1)
#     discriminator = models.Model(input_img, out, name='Discriminator')

#     discriminator.summary()
#     return discriminator

# # D = build_discriminator((64, 64, 3))

"""# **GAN:**"""

# 建構GAN 
def build_gan(latent_dim, generator, discriminator):
    gan_input = keras.Input(shape=(latent_dim,), name='GAN_input')
    img = generator(gan_input)
    # 凍結Discriminator的權重(只對Generator做訓練)
    # discriminator.trainable = False         # Turn ON (可加可不加)
    gan_output = discriminator(img)
    # discriminator.trainable = True         # Turn OFF
    gan = models.Model(gan_input, gan_output, name='GAN')

    gan.summary()
    return gan

# build_gan(128, G, D)
# trainable-params only in G and D

"""# **Initialization:**"""

# -----------------
#    初始化 
# -----------------

# 儲存Loss＆Accuracy
# G_Losses = []                                   ###
# D_Losses = []
# D_Accuracies = []

# 儲存路徑
save_dir = "/content/drive/MyDrive/Colab Notebooks/saves"
# images_dir_name = "generated_images_1024_noise0.1_lr0.0001_FFHQ"
# model_dir_name = "model_1024_noise0.1_lr0.0001_FFHQ"
# loss_dir_name = "Loss&Acc_1024_noise0.1_lr0.0001_FFHQ"

# 設定潛在空間維度
latent_dim = 128
img_shape = (128, 128, 3)
batch_size = 256 # 256 or more (dataset batch記得改)
# lr最好跟batch_size一起xN倍
epochs = 100
# 設定標籤的雜訊
noise = 0.05    # *0.05
num2generate = 5


# 固定的random_vectors，方便觀察epoch間變化
fixed_random_vectors = tf.random.normal(shape=(num2generate, latent_dim))
# file = open(os.path.join(save_dir, loss_dir_name, "vectorZ.txt"),'w')
# file.write(str(fixed_random_vectors))
# file.close()

# model初始化
generator = build_generator(latent_dim)                     ###
discriminator  = build_discriminator(img_shape)
gan = build_gan(latent_dim, generator, discriminator)

# 優化器＆學習率設定
# 自適應優化器Adam <-> SGD
D_optimizer = keras.optimizers.Adam(learning_rate=0.0001, beta_1=0.5)     # 0.00005
G_optimizer = keras.optimizers.Adam(learning_rate=0.0001, beta_1=0.5)     # 0.0002
# D_optimizer = keras.optimizers.RMSprop(learning_rate=0.0001)     # 0.00005
# G_optimizer = keras.optimizers.RMSprop(learning_rate=0.0001)     # 0.0002

# 損失函數定義
# 默認: from_logits=False輸出為機率[0, 1]與softmax相同
# from_logits=True，輸出分布[-inf, inf]
loss_function = keras.losses.BinaryCrossentropy(from_logits=True)
# BCE: -w(p(x)log x +(1 - p(x))log(1 - x))
# 公式寫法的loss function:
# D_loss_function = -tf.reduce_mean(tf.log(prob_true) + tf.log(1-prob_fake))
# G_loss_function = tf.reduce_mean(tf.log(1-fake))

TRAIN_LOGDIR = os.path.join(save_dir, "WGAN_nor", 'train_data')
file_writer = tf.summary.create_file_writer(TRAIN_LOGDIR)

"""# **Train:**

```
# WGAN Version
```
"""

from tensorflow.keras import backend as K

EPOCHs = 200
LAMBDA = 10
CURRENT_EPOCH = 1 # Epoch start from
SAVE_EVERY_N_EPOCH = 5 # Save checkpoint at every n epoch
N_CRITIC = 3 # Train critic(discriminator) n times then train generator 1 time.
LR = 1e-4
MIN_LR = 0.000001 # Minimum value of learning rate
DECAY_FACTOR=1.00004 # learning rate decay factor
current_learning_rate = LR
trace = True
n_critic_count = 0

# 恢復weights
checkpoint_path = os.path.join(save_dir, "WGAN_nor", "checkpoints")

ckpt = tf.train.Checkpoint(generator=generator,
                           discriminator=discriminator,
                           G_optimizer=G_optimizer,
                           D_optimizer=D_optimizer)

ckpt_manager = tf.train.CheckpointManager(ckpt, checkpoint_path, max_to_keep=5)
ckpt.restore(ckpt_manager.latest_checkpoint)

checkpoint_path = os.path.join(save_dir, "WGAN_nor", "checkpoints")

ckpt = tf.train.Checkpoint(generator=generator,
                           discriminator=discriminator,
                           G_optimizer=G_optimizer,
                           D_optimizer=D_optimizer)

ckpt_manager = tf.train.CheckpointManager(ckpt, checkpoint_path, max_to_keep=None)

# if a checkpoint exists, restore the latest checkpoint.
if ckpt_manager.latest_checkpoint:
    ckpt.restore(ckpt_manager.latest_checkpoint)
    latest_epoch = int(ckpt_manager.latest_checkpoint.split('-')[1])
    CURRENT_EPOCH = latest_epoch * SAVE_EVERY_N_EPOCH
    print ('Latest checkpoint of epoch {} restored!!'.format(CURRENT_EPOCH))

def generate_and_save_images(model, epoch, test_input, figure_size=(12,6), subplot=(3,6), save=True, is_flatten=False):
    '''
        Generate images and plot it.
    '''
    predictions = model.predict(test_input)
    if is_flatten:
        predictions = predictions.reshape(-1, 128, 128, 3).astype('float32')
    fig = plt.figure(figsize=figure_size)
    for i in range(predictions.shape[0]):
        axs = plt.subplot(subplot[0], subplot[1], i+1)
        plt.imshow(predictions[i] * 0.5 + 0.5)
        plt.axis('off')
    if save:
        plt.savefig(os.path.join(save_dir, "WGAN_nor", "generated_imgs", 'image_at_epoch_{:04d}.png'.format(epoch)))
    plt.show()

num_examples_to_generate = 18
# We will reuse this seed overtime
sample_noise = tf.random.normal([num_examples_to_generate, latent_dim])
# generate_and_save_images(generator, 0, [sample_noise], figure_size=(12,6), subplot=(3,6), save=False, is_flatten=False)

def learning_rate_decay(current_lr, decay_factor=DECAY_FACTOR):
    '''
        Calculate new learning rate using decay factor
    '''
    new_lr = max(current_lr / decay_factor, MIN_LR)
    return new_lr

def set_learning_rate(new_lr):
    '''
        Set new learning rate to optimizers
    '''
    K.set_value(D_optimizer.lr, new_lr)
    K.set_value(G_optimizer.lr, new_lr)

@tf.function
def WGAN_GP_train_d_step(real_image, batch_size, step):
    '''
        One discriminator training step
        Reference: https://www.tensorflow.org/tutorials/generative/dcgan
    '''
    print("retrace")
    noise = tf.random.normal([batch_size, latent_dim])
    epsilon = tf.random.uniform(shape=[batch_size, 1, 1, 1], minval=0, maxval=1)
    ###################################
    # Train D
    ###################################
    with tf.GradientTape(persistent=True) as d_tape:
        with tf.GradientTape() as gp_tape:
            fake_image = generator([noise], training=True)
            fake_image_mixed = epsilon * tf.dtypes.cast(real_image, tf.float32) + ((1 - epsilon) * fake_image)
            fake_mixed_pred = discriminator([fake_image_mixed], training=True)
            
        # Compute gradient penalty                          (原本的LossFunction變成此處的W距離)
        grads = gp_tape.gradient(fake_mixed_pred, fake_image_mixed)
        grad_norms = tf.sqrt(tf.reduce_sum(tf.square(grads), axis=[1, 2, 3]))
        gradient_penalty = tf.reduce_mean(tf.square(grad_norms - 1))
        
        fake_pred = discriminator([fake_image], training=True)
        real_pred = discriminator([real_image], training=True)
        
        D_loss = tf.reduce_mean(fake_pred) - tf.reduce_mean(real_pred) + LAMBDA * gradient_penalty    # WGAN LossFuncion ！
    # Calculate the gradients for discriminator
    D_gradients = d_tape.gradient(D_loss,
                                            discriminator.trainable_variables)
    # Apply the gradients to the optimizer
    D_optimizer.apply_gradients(zip(D_gradients,
                                                discriminator.trainable_variables))
    # Write loss values to tensorboard
    if step % 10 == 0:
        with file_writer.as_default():
            tf.summary.scalar('D_loss', tf.reduce_mean(D_loss), step=step)

@tf.function
def WGAN_GP_train_g_step(real_image, batch_size, step):
    '''
        One generator training step
        
        Reference: https://www.tensorflow.org/tutorials/generative/dcgan
    '''
    print("retrace")
    noise = tf.random.normal([batch_size, latent_dim])
    ###################################
    # Train G
    ###################################
    with tf.GradientTape() as g_tape:
        fake_image = generator([noise], training=True)
        fake_pred = discriminator([fake_image], training=True)
        G_loss = -tf.reduce_mean(fake_pred)
    # Calculate the gradients for generator
    G_gradients = g_tape.gradient(G_loss,
                                            generator.trainable_variables)
    # Apply the gradients to the optimizer
    G_optimizer.apply_gradients(zip(G_gradients,
                                                generator.trainable_variables))
    # Write loss values to tensorboard
    if step % 10 == 0:
        with file_writer.as_default():
            tf.summary.scalar('G_loss', G_loss, step=step)


for epoch in range(CURRENT_EPOCH, EPOCHs + 1):
    start = time.time()
    print('Start of epoch %d' % (epoch,))
    # Using learning rate decay
    current_learning_rate = learning_rate_decay(current_learning_rate)
    print('current_learning_rate %f' % (current_learning_rate,))
    set_learning_rate(current_learning_rate)
    
    for step, (image) in enumerate(tqdm(dataset)):
        current_batch_size = image.shape[0]
        # Train critic (discriminator)
        WGAN_GP_train_d_step(image, batch_size=tf.constant(current_batch_size, dtype=tf.int64), step=tf.constant(step, dtype=tf.int64))
        n_critic_count += 1
        if n_critic_count >= N_CRITIC: 
            # Train generator
            WGAN_GP_train_g_step(image, batch_size= tf.constant(current_batch_size, dtype=tf.int64), step=tf.constant(step, dtype=tf.int64))
            n_critic_count = 0
        
        if step % 10 == 0:
            print ('.', end='')
    
    # Using a consistent sample so that the progress of the model is clearly visible.
    generate_and_save_images(generator, epoch, [sample_noise], figure_size=(12,6), subplot=(3,6), save=True, is_flatten=False)
    
    if epoch % SAVE_EVERY_N_EPOCH == 0:
        ckpt_save_path = ckpt_manager.save()
        print ('Saving checkpoint for epoch {} at {}'.format(epoch,
                                                             ckpt_save_path))
    
    print ('Time taken for epoch {} is {} sec\n'.format(epoch,
                                                      time.time()-start))
    
# Save at final epoch
ckpt_save_path = ckpt_manager.save()
print ('Saving checkpoint for epoch {} at {}'.format(EPOCHs,
                                                        ckpt_save_path))

"""

```
# DCGAN Version
```

"""

# -----------------
#  開始訓練網路         @tf.function
# -----------------
def get_random_vectors(batch_size, latent_dim):
  vectors = tf.random.normal(shape=(batch_size, latent_dim))
  return vectors

def get_labels(batch_size, noise):
  # ------- important -------
  # 準備label，並加入隨機雜訊
  # ---------------------------
  real_labels = tf.ones((batch_size, 1))
  # np.ones((batch_size, 1))
  real_labels += noise * tf.random.uniform(real_labels.shape)   # [0, 1)
  # np.random.random(fake_labels.shape)
  fake_labels = tf.zeros((batch_size, 1))
  fake_labels += noise * tf.random.uniform(fake_labels.shape)
  return real_labels, fake_labels

def cal_d_loss(D_real, D_fake, noise):
  real_labels, fake_labels = get_labels(D_real.shape[0], noise)
  real_loss = loss_function(real_labels, D_real)
  fake_loss = loss_function(fake_labels, D_fake)
  # real_loss＆fake_loss的平均
  d_loss = 0.5 * tf.add(real_loss, fake_loss)   # 因.GradientTape()該使用tf而非np (缺少id屬性)
  return d_loss

def cal_g_loss(gan_out, noise):
  real_labels, fake_labels = get_labels(gan_out.shape[0], noise)
  g_loss = loss_function(real_labels, gan_out)
  return g_loss


# ------- important -------
#   修飾器@tf.function
# py轉譯成tensorflow計算圖(Autograph)
#    Eager Execution
# ---------------------------
@tf.function      # tf.Session + 計算圖
def train_network(batch_imgs):
    random_latent_vectors = get_random_vectors(batch_size, latent_dim)    # 要不要分別寫進GradientTape()? No.

    # ---------------------
    #  訓練Discriminator 
    # ---------------------
    with tf.GradientTape() as D_tape:                    # or train_on_batch()

      # ------- important -------
      # 由於generator中BN層的mean跟std
      # True: 只使用當前batch的資料 (training mode)
      # False: 使用moving statistics (inference mode)
      # ---------------------------
      generated_img = generator(random_latent_vectors, training=True)     # 要寫進GradientTape()
      # (正向傳播)
      D_real = discriminator(batch_imgs, training=True)     # D_real, D_fake -> (0, 1) | sigmoid
      D_fake = discriminator(generated_img, training=True)
      d_loss = cal_d_loss(D_real, D_fake, noise)
      # sigmoid輸出，生成圖片為真的機率(獨立)
      d_acc = tf.math.reduce_mean(D_fake)          # 取平均
      
      # (反向傳播)
    grads = D_tape.gradient(d_loss, discriminator.trainable_variables)
    d_optimizer.apply_gradients(zip(grads, discriminator.trainable_variables))

    # ---------------------
    #   訓練Generator 
    # ---------------------
    with tf.GradientTape() as G_tape:

      # (正向傳播)
      # ---------------------
      #   training=True
      # ---------------------
      gan_out = gan(random_latent_vectors, training=True)         # gan_out -> (-1, 1) | tanh      
      g_loss = cal_g_loss(gan_out, noise)
      
      # (反向傳播)
    grads = G_tape.gradient(g_loss, generator.trainable_variables)
    g_optimizer.apply_gradients(zip(grads, generator.trainable_variables))
    return d_loss, d_acc, g_loss      # Eager Execution .numpy()



def train(dataset, epochs):

  # 一個完整Epoch (full dataset)
  for epoch in range(epochs):
    print("")
    print("==============> Epoch[{}] training:".format(epoch + 1))                                      # +1
    # 計時
    start_time = time.time()
    # 一次的Iterations (處理一個batch)
    for iterations, batch_imgs in enumerate(tqdm(dataset)):     # tqdm

      d_loss, d_acc, g_loss = train_network(batch_imgs)
      D_Losses.append(d_loss.numpy())         # .numpy()
      D_Accuracies.append(d_acc.numpy())
      G_Losses.append(g_loss.numpy())
      # print loss＆Acc + 進度條
      if iterations % 100 == 0: 
        # print(" ")
        print(" \t\t\tIteration: [{}] [D_loss: {:.3f}, G_loss: {:.3f}] [Acc: {:.3f}]"
                      .format(iterations, D_Losses[-1], G_Losses[-1], D_Accuracies[-1]))
    
    # 保存結果
    save_images(generator, epoch, fixed_random_vectors, num2generate)
    save_models(generator, discriminator, epoch)
    save_losses(D_Losses, G_Losses, D_Accuracies)
    # 計算這個Epoch所花費的時間
    end_time = time.time()
    print("-----------------------------")
    print("Training time: {:6.2f} sec".format(end_time - start_time))


# ---------------------
#    保存結果 
# ---------------------
def save_images(generator, epoch, vectors, num2generate):
  # random_vectors = tf.random.normal(shape=(num2generate, latent_dim))  # 改用固定vector

  # training設為False
  # 讓BN層使用moving statistics來執行圖片生成
  results = generator(vectors, training=False)

  # 把results轉回rgb格式
  results *= 255.
  results.numpy()

  fig = plt.figure(figsize=(16, 16))
  # 保存目前Epoch的生成圖片成果(5 imgs per epoch)
  for i in range(num2generate):
    imgs = keras.preprocessing.image.array_to_img(results[i])
    # imgs.save(os.path.join(save_dir, "generated_images_1024", "generated_img_{epoch}_{i}.png").format(epoch=(epoch + 1), i=i))
    plt.subplot(1, 5, i+1)
    plt.imshow(imgs)
    plt.axis('off')
  plt.savefig(os.path.join(save_dir, images_dir_name, "images_at_epoch_{:03d}.png").format(epoch + 1))                    # +1
  plt.show()


def save_models(generator, discriminator, epoch):
  # 保存模型＆權重
  generator.save(os.path.join(save_dir, model_dir_name, "Generator_epoch{}.h5").format(epoch + 1))                      # +1
  discriminator.save(os.path.join(save_dir, model_dir_name, "Discriminator_epoch{}.h5").format(epoch + 1))                  # +1


def save_losses(D_Losses, G_Losses, D_Accuracies):
  # 保存Losses＆Accuracies
  file = open(os.path.join(save_dir, loss_dir_name, "d_loss.txt"),'w')
  file.write(str(D_Losses))
  file.close()

  file = open(os.path.join(save_dir, loss_dir_name, "g_loss.txt"),'w')
  file.write(str(G_Losses))
  file.close()

  file = open(os.path.join(save_dir, loss_dir_name, "d_acc.txt"),'w')
  file.write(str(D_Accuracies))
  file.close()

train(dataset, epochs)

# ---------------------
#  畫出Loss & Acc
# ---------------------
iterations = range(1, len(D_Losses) + 1)

def draw_loss_acc(iteration, loss_dir_name):
  plt.figure()
  plt.plot(iteration, D_Losses, 'r', label="Discriminate Loss")
  plt.plot(iteration, G_Losses, 'b', label="Generate Loss")
  plt.title("Training Loss")
  plt.xlabel("Iteration")
  plt.ylabel("Loss")
  plt.legend()
  # plt.savefig(os.path.join(save_dir, loss_dir_name, "Loss.png"))
  plt.show()

  plt.figure()
  plt.plot(iteration, D_Accuracies, 'g--', label="Discriminator Acc")
  plt.title("Accuracy of Discriminator")
  plt.xlabel("Iteration")
  plt.ylabel("Accuracy")
  plt.legend()
  # plt.savefig(os.path.join(save_dir, loss_dir_name, "Accuracy.png"))
  plt.show()


# 曲線平滑化 (EMA)
def smooth_curve(points, factor=0.8):
    smoothed_points = []
    for point in points:
        if smoothed_points:
            previous = smoothed_points[-1]
            smoothed_points.append(previous * factor + point * (1 - factor))
        else:
            smoothed_points.append(point)
    return smoothed_points


def drawsmooth_loss_acc(iteration, loss_dir_name):
  plt.figure()
  plt.plot(iteration, smooth_curve(D_Losses), 'r', label="Smoothed Discriminate Loss")
  plt.plot(iteration, smooth_curve(G_Losses), 'b', label="Smoothed Generate Loss")
  plt.title("Smoothed Training Loss")
  plt.xlabel("Iteration")
  plt.ylabel("Loss")
  plt.legend()
  # plt.savefig(os.path.join(save_dir, loss_dir_name, "Smoothed_Loss.png"))
  plt.show()

  plt.figure()
  plt.plot(iteration, smooth_curve(D_Accuracies), 'g--', label="Discriminator Acc")
  plt.title("Smoothed Accuracy of Discriminator")
  plt.xlabel("Iteration")
  plt.ylabel("Accuracy")
  plt.legend()
  # plt.savefig(os.path.join(save_dir, loss_dir_name, "Smoothed_Accuracy.png"))
  plt.show()


save_dir = "/content/drive/MyDrive/Colab Notebooks/saves"
# loss_dir_name = "Loss&Acc_1024_noise0.1_lr0.0001_FFHQ"
draw_loss_acc(iterations, loss_dir_name)
drawsmooth_loss_acc(iterations, loss_dir_name)

# GIF
import glob
import imageio

images_dir_name = "generated_imgs"

anim_file = os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", "WGAN_nor",images_dir_name, "my_dcgan.gif")

with imageio.get_writer(anim_file, mode='I') as writer:
  filenames = glob.glob(os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", "WGAN_nor",images_dir_name, 'image*.png'))
  filenames = sorted(filenames)
  for filename in filenames:
    image = imageio.imread(filename)
    writer.append_data(image)
  image = imageio.imread(filename)
  writer.append_data(image)

"""# **意外中斷恢復訓練:**"""

def load_models(epoch, model_dir_name):
  generator = keras.models.load_model(os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", model_dir_name, "Generator_epoch{}.h5")
                                                                    .format(epoch))
  generator.summary()
  discriminator = keras.models.load_model(os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", model_dir_name, "Discriminator_epoch{}.h5")
                                                                      .format(epoch))
  discriminator.summary()
  return generator, discriminator

def load_losses(loss_dir_name):
  with open(os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", loss_dir_name, "g_loss.txt"), 'r') as files:
    G_Losses = files.read()
  G_Losses = eval(G_Losses)
  print("g_loss: length={} type={}".format(len(G_Losses), type(G_Losses)))
  
  with open(os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", loss_dir_name, "d_loss.txt"), 'r') as files:
    D_Losses = files.read()
  D_Losses = eval(D_Losses)
  print("d_loss: length={} type={}".format(len(D_Losses), type(D_Losses)))

  with open(os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", loss_dir_name, "d_acc.txt"), 'r') as files:
    D_Accuracies = files.read()
  D_Accuracies = eval(D_Accuracies)
  print("d_acc: length={} type={}".format(len(D_Accuracies), type(D_Accuracies)))
  return G_Losses, D_Losses, D_Accuracies


model_dir_name = "model_1024_noise0.1_lr0.0001_FFHQ"
loss_dir_name = "Loss&Acc_1024_noise0.1_lr0.0001_FFHQ"
epoch = 23
# generator, discriminator = load_models(epoch, model_dir_name)
G_Losses, D_Losses, D_Accuracies = load_losses(loss_dir_name)

"""# **載入已訓練模型生成圖片:**"""

def get_models(epoch, model_dir_name):
  generator = keras.models.load_model(os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", model_dir_name, "Generator_epoch{}.h5")
                                                                    .format(epoch))
  generator.summary()
  discriminator = keras.models.load_model(os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", model_dir_name, "Discriminator_epoch{}.h5")
                                                                      .format(epoch))
  discriminator.summary()
  return generator, discriminator

def generating(num2generate, latent_dim, epoch, images_dir_name):
  random_vectors = tf.random.normal(shape=(num2generate, latent_dim))
  results = generator(random_vectors, training=False)
  results *= 255.
  results.numpy()

  fig = plt.figure(figsize=(50, 50))
  for i in range(num2generate):
    imgs = keras.preprocessing.image.array_to_img(results[i])
    # imgs.save("generated_img_{i}.png".format(epoch=epoch, i=i))
    plt.subplot(10, 10, i+1)
    plt.imshow(imgs)
    plt.axis('off')
  plt.savefig(os.path.join("/content/drive/MyDrive/Colab Notebooks/saves", images_dir_name, "images_at_epoch_({}).png").format(epoch))
  plt.savefig("1.png")
  plt.show()



model_dir_name = "WGAN_nor/generated_imgs"
images_dir_name = "WGAN_nor/generated_imgs"
epoch = 100
# generator, discriminator = get_models(epoch, model_dir_name)
generating(100, 128, epoch, images_dir_name)
