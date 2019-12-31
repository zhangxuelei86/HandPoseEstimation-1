import numpy as np
import numpy
import h5py
import cv2
import scipy.io as sio
import sys
import os
import math
import matplotlib.pyplot
import matplotlib.pyplot as plt

dataset_path = 'H:/HandPoseEstimation/dataset/NYU'

J = 31
# joint_id = np.array([0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 5, 11, 17, 23, 32, 30, 31, 28, 27, 25, 24])
img_size = 128
joint_id = np.array([0, 3, 6, 9, 12, 15, 18, 21, 24, 25, 27, 30, 31, 32])

fx = 588.03
fy = 587.07
fu = 320. #57
fv = 240. #43


def figure_joint_skeleton(dm, uvd_pt, flag):

    if flag:
        for i in range(len(uvd_pt)):
            uvd_pt[i, 0] = (uvd_pt[i, 0] + 1) / 2 * 128
            uvd_pt[i, 1] = (-uvd_pt[i, 1] + 1) / 2 * 128

    fig = matplotlib.pyplot.figure()
    ax = fig.add_subplot(1,1,1)
    ax.imshow(dm, cmap=matplotlib.cm.gray)
    ax.axis('off')

    fig_color = ['c', 'm', 'y', 'g', 'r']
    for f in range(5):
        ax.plot([uvd_pt[f*2,0], uvd_pt[f*2+1,0]],
                [uvd_pt[f*2,1], uvd_pt[f*2+1,1]], color=fig_color[f], linewidth=2)
        ax.scatter(uvd_pt[f*2,0],uvd_pt[f*2,1],s=30,c=fig_color[f])
        ax.scatter(uvd_pt[f*2+1,0],uvd_pt[f*2+1,1],s=30,c=fig_color[f])
        if f < 4:
            ax.plot([uvd_pt[13,0], uvd_pt[f*2+1,0]],
                    [uvd_pt[13,1], uvd_pt[f*2+1,1]], color=fig_color[f], linewidth=2)
    ax.plot([uvd_pt[9,0], uvd_pt[10,0]],
            [uvd_pt[9,1], uvd_pt[10,1]], color='r', linewidth=2)

    ax.scatter(uvd_pt[13,0], uvd_pt[13,1], s=100, c='w')
    ax.scatter(uvd_pt[11,0], uvd_pt[11,1], s=50, c='b')
    ax.scatter(uvd_pt[12,0], uvd_pt[12,1], s=50, c='b')

    ax.plot([uvd_pt[13,0], uvd_pt[11,0]],
            [uvd_pt[13,1], uvd_pt[11,1]], color='b', linewidth=2)
    ax.plot([uvd_pt[13,0], uvd_pt[12,0]],
            [uvd_pt[13,1], uvd_pt[12,1]], color='b', linewidth=2)
    ax.plot([uvd_pt[13,0], uvd_pt[10,0]],
            [uvd_pt[13,1], uvd_pt[10,1]], color='r', linewidth=2)

    return fig


## This part of code is modified from [DeepPrior](https://cvarlab.icg.tugraz.at/projects/hand_detection/)
def cropImage(depth, com, cube_size):

      u, v, d = com # u,v,d = [218.66824341 287.33966064 765.08984375]

      zstart = d - cube_size / 2. # 615.08984375
      zend = d + cube_size / 2. # 915.08984375

      xstart = int(math.floor((u * d / fx - cube_size / 2.) / d * fx)) # 103
      xend = int(math.floor((u * d / fx + cube_size / 2.) / d * fx)) # 333
      ystart = int(math.floor((v * d / fy - cube_size / 2.) / d * fy)) # 172
      yend = int(math.floor((v * d / fy + cube_size / 2.) / d * fy)) # 402

      # shape: (230,230)
      cropped = depth[max(ystart, 0):min(yend, depth.shape[0]), max(xstart, 0):min(xend, depth.shape[1])].copy()

      # shape: (230,230)
      cropped = np.pad(cropped, ((abs(ystart)-max(ystart, 0), abs(yend)-min(yend, depth.shape[0])),
                                    (abs(xstart)-max(xstart, 0), abs(xend)-min(xend, depth.shape[1]))), mode='constant', constant_values=0)

      msk1 = np.bitwise_and(cropped < zstart, cropped != 0) # shape: (230,230)
      msk2 = np.bitwise_and(cropped > zend, cropped != 0) # shape: (230,230)

      cropped[msk1] = zstart
      cropped[msk2] = zend # shape: (34637, )

      # print("cropped.shape", cropped.shape)

      dsize = (img_size, img_size) # (128,128)
      wb = (xend - xstart) # 230
      hb = (yend - ystart) # 230

      if wb > hb:
        sz = (int(dsize[0]), int(hb * dsize[0] / wb))
      else:
        sz = (int(wb * dsize[1] / hb), int(dsize[1])) # (128,128)

      roi = cropped
      rz = cv2.resize(cropped, sz) # (128,128)

      ret = np.ones(dsize, np.float32) * zend # (128,128)

      xstart = int(math.floor(dsize[0] / 2 - rz.shape[1] / 2)) # 0
      xend = int(xstart + rz.shape[1]) # 128

      ystart = int(math.floor(dsize[1] / 2 - rz.shape[0] / 2)) # 0
      yend = int(ystart + rz.shape[0]) # 128

      ret[ystart:yend, xstart:xend] = rz

      return ret


def show_joints(depth, com, joint_uvd):

    cube_size = 300

    u, v, d = com
    zstart = d - cube_size / 2.
    zend = d + cube_size / 2.
    print(u, v, d)

    xstart = int(math.floor((u * d / fx - cube_size / 2.) / d * fx))  # 103
    xend = int(math.floor((u * d / fx + cube_size / 2.) / d * fx))  # 333
    ystart = int(math.floor((v * d / fy - cube_size / 2.) / d * fy))  # 172
    yend = int(math.floor((v * d / fy + cube_size / 2.) / d * fy))  # 402

    msk1 = np.bitwise_and(depth < zstart, depth != 0)  # shape: (230,230)
    msk2 = np.bitwise_and(depth > zend, depth != 0)  # shape: (230,230)

    depth[msk1] = zstart
    depth[msk2] = zend

    fig = figure_joint_skeleton(depth, joint_uvd, 0)
    ax = fig.add_subplot(1, 1, 1)

    ax.imshow(depth, cmap=matplotlib.cm.gray)
    ax.set_xlim(xstart, xend)
    ax.set_ylim(ystart, yend)
    # # matplotlib.pyplot.savefig('result_crop1.png')
    #
    # fig.canvas.draw()
    # data = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
    # data = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    #
    # data = np.flip(data, 0)

    return fig


def jointImgTo3D(sample):
    """
    Normalize sample to metric 3D
    :param sample: joints in (x,y,z) with x,y in image coordinates and z in mm
    :return: normalized joints in mm
    """
    ret = np.zeros((3,), np.float32)
    # convert to metric using f
    ret[0] = (sample[0]-fu)*sample[2]/fx
    ret[1] = (fv-sample[1])*sample[2]/fy
    ret[2] = sample[2]
    return ret

def jointsImgTo3D(sample):
    """
    Normalize sample to metric 3D
    :param sample: joints in (x,y,z) with x,y in image coordinates and z in mm
    :return: normalized joints in mm
    """
    ret = np.zeros((sample.shape[0], 3), np.float32)
    for i in range(sample.shape[0]):
        ret[i] = jointImgTo3D(sample[i])
    return ret

def joint3DToImg(sample):
    """
    Denormalize sample from metric 3D to image coordinates
    :param sample: joints in (x,y,z) with x,y and z in mm
    :return: joints in (x,y,z) with x,y in image coordinates and z in mm
    """
    ret = np.zeros((3, ), np.float32)
    if sample[2] == 0.:
        ret[0] = fu
        ret[1] = fv
        return ret
    ret[0] = sample[0]/sample[2]*fx+fu
    ret[1] = fv-sample[1]/sample[2]*fy
    ret[2] = sample[2]
    return ret

def joints3DToImg(sample):
    """
    Denormalize sample from metric 3D to image coordinates
    :param sample: joints in (x,y,z) with x,y and z in mm
    :return: joints in (x,y,z) with x,y in image coordinates and z in mm
    """
    ret = np.zeros((sample.shape[0], 3), np.float32)
    for i in range(sample.shape[0]):
        ret[i] = joint3DToImg(sample[i])
    return ret

def rotatePoint2D(p1, center, angle):
    """
    Rotate a point in 2D around center
    :param p1: point in 2D (u,v,d)
    :param center: 2D center of rotation
    :param angle: angle in deg
    :return: rotated point
    """
    alpha = angle * numpy.pi / 180.
    pp = p1.copy()
    pp[0:2] -= center[0:2]
    pr = numpy.zeros_like(pp)
    pr[0] = pp[0]*numpy.cos(alpha) - pp[1]*numpy.sin(alpha)
    pr[1] = pp[0]*numpy.sin(alpha) + pp[1]*numpy.cos(alpha)
    pr[2] = pp[2]
    ps = pr
    ps[0:2] += center[0:2]
    return ps


def rotatePoints2D(pts, center, angle):
    """
    Transform points in 2D coordinates
    :param pts: point coordinates
    :param center: 2D center of rotation
    :param angle: angle in deg
    :return: rotated points
    """
    ret = pts.copy()
    for i in range(pts.shape[0]):
        ret[i] = rotatePoint2D(pts[i], center, angle)
    return ret

def rotateHand(dpt, cube_size, com, rot, joints3D, pad_value=0):
    '''
    rotate the depth image
    :param dpt: cropped depth image
    :param cube_size: the cube size
    :param com: com
    :param rot: rotation angle
    :param joints3D: the ground truth
    :param pad_value:
    :return: rotated image and joints
    '''

    # if rot is 0, nothing to do
    if numpy.allclose(rot, 0.):
        return dpt, joints3D, rot

    rot = numpy.mod(rot, 360)

    # rotate depth image at com
    M = cv2.getRotationMatrix2D((com[0], com[1]), -rot, 1)
    new_dpt = cv2.warpAffine(dpt, M, (dpt.shape[1], dpt.shape[0]), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=pad_value)
    # rotate poses at com
    com3D = jointImgTo3D(com)
    joint_2D = joints3DToImg(joints3D)
    data_2D = numpy.zeros_like(joint_2D)
    for k in range(data_2D.shape[0]):
        data_2D[k] = rotatePoint2D(joint_2D[k], com[0:2], rot)
    new_joints3D = jointsImgTo3D(data_2D)

    # crop the rotated image, and normalize image and pose
    depth = cropImage(new_dpt, com, cube_size)  # shape: (128,128)
    depth_norm = (depth - com[2]) / (cube_size / 2.)
    joint_norm = (new_joints3D - com3D) / (cube_size / 2.)

    return depth_norm, joint_norm


def translationHand(dpt, cube_size, com, offset, joints3D):
    '''
    translate the depth image
    :param dpt: cropped depth image
    :param cube_size: the cube size
    :param com: com
    :param offset: translation offset
    :param joints3D: the ground truth
    :return: the translated depth image and joints
    '''

    # add offset to com3D
    newCom3D = jointImgTo3D(com) + offset

    # add offset to com2D
    newCom2D = joint3DToImg(newCom3D)

    # crop the original depth image
    depth = cropImage(dpt, newCom2D, cube_size)  # shape: (128,128)

    # normalized the depth image and poses
    depth_norm = (depth - newCom2D[2]) / (cube_size / 2.)
    joint_norm = (joints3D - newCom3D) / (cube_size / 2.)

    return depth_norm, joint_norm

def scaleHand(dpt, cube_size, sc, com, joints3D):
    '''
    scale the depth images
    :param dpt: depth image
    :param cube_size: the cube size
    :param sc: scale factor
    :param com: com
    :param joints3D: the ground truth
    :return: the scaled depth image and joints
    '''
    # scale the original size
    new_cube_size = cube_size * sc

    # crop the original depth image
    com3D = jointImgTo3D(com)

    depth = cropImage(dpt, com, new_cube_size)  # shape: (128,128)

    # normalized the depth images and poses
    depth_norm = (depth - com[2]) / (new_cube_size / 2.)
    joint_norm = (joints3D - com3D) / (new_cube_size / 2.)

    return depth_norm, joint_norm



# data_names =   ['test']
# cube_sizes =   [300]
# id_starts =    [0]
# id_ends =      [8252]
# num_packages = [3]
#
# depth_center = np.zeros(((8252, 128, 128)))
# joint_xyz_center = np.zeros(((8252, 14, 3)))
#
# for D in range(0, len(data_names)):
#
#     data_name = data_names[D]   # train
#     cube_size = cube_sizes[D]   # 340
#     id_start = id_starts[D]     # 0
#     id_end = id_ends[D]         # 72756
#     chunck_size = (id_end - id_start) / num_packages[D] #(72756-0)/3 = 24252
#
#     data_type = 'train' if data_name == 'train' else 'test'  # train
#     data_path = '{}/{}'.format(dataset_path, data_type)      # NYU/train/
#     label_path = '{}/joint_data.mat'.format(data_path)       # NYU/train/joint_data.mat
#
#     print(label_path)
#
#     labels = sio.loadmat(label_path)
#     joint_uvd = labels['joint_uvd'][0]  # shape: (72757,36,3)
#     joint_xyz = labels['joint_xyz'][0]  # shape: (72757,36,3)
#
#     for id in range(id_start, id_end):
#
#         img_path = '{}/depth_1_{:07d}.png'.format(data_path, id + 1)  # NYU/train/depth_1_{:07d}.png
#         print(img_path)
#
#         if not os.path.exists(img_path):
#             print('{} Not Exists!'.format(img_path))
#             continue
#
#         img = cv2.imread(img_path) # shape:(480,640,3)
#         ori_depth = np.asarray(img[:, :, 0] + img[:, :, 1]*256) #shape: (480,640)
#
#         depth = cropImage(ori_depth, joint_uvd[id, 34], cube_size=300) #shape: (128,128)
#         com3D = joint_xyz[id, 34] # shape: (3, )
#
#         depth_crop = (depth - com3D[2]) / 150
#         joint_center = (joint_xyz[id][joint_id] - com3D) / 150 # shape: (31,3)->(14,3)
#
#         depth_center[id] = depth_crop
#         joint_xyz_center[id] = joint_center
#
# np.save('H:/HandPoseEstimation/dataset/NYU/NYU_Image_Test.npy',depth_center)
# np.save('H:/HandPoseEstimation/dataset/NYU/NYU_Label_Test.npy',joint_xyz_center)
#
# print("depth_center.shape", depth_center.shape)
# print("joint_xyz_center.shape", joint_xyz_center.shape)
#
# print("depth[0]: ", depth_center[0])
# print("joint[0]: ", joint_xyz_center[0])

