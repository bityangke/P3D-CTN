#!/usr/bin/env python

import _init_paths
import os, sys, pdb
import argparse
import numpy as np
import action_util as action
from datasets.ucfsports import ucfsports
from fast_rcnn.config import cfg
import cPickle as pickle
import caffe

def parse_args():
    """Parse input arguments."""
    parser = argparse.ArgumentParser(description='Faster R-CNN for actino detection')
    parser.add_argument('--gpu', dest='gpu_id', help='GPU device id to use [0]',
                        default=0, type=int)
    parser.add_argument('--cpu', dest='cpu_mode',
                        help='Use CPU mode (overrides --gpu)',
                        action='store_true')
    parser.add_argument('--proto', dest='proto', help='the caffe prototxt file')
    parser.add_argument('--net', dest='net', help='the caffe net model file')
    parser.add_argument('--imdb', dest='imdb', help='which imdb file to test')
    parser.add_argument('--out', dest='savepath', help='where to save the detection results (pickle)')
    args = parser.parse_args()

    return args

if __name__ == '__main__':
    args = parse_args()
    if not os.path.isfile(args.net):
        raise IOError(('{:s} not found.').format(args.net))
    
    cfg.TEST.HAS_RPN = True
    cfg.TEST.SCALES = [600]

    MOD = args.imdb.split('_')[1]
    LEN = int(args.imdb.split('_')[2])
    if MOD=='FLOW' and LEN==1: cfg.PIXEL_MEANS = np.array([[[128., 128., 128.]]])
    if MOD=='FLOW' and LEN==5: cfg.PIXEL_MEANS = np.array([[[128., 128., 128.]*5]])

    ucfsports_test = ucfsports(args.imdb, 'TEST')
    roidb = ucfsports_test.roidb

    if not os.path.exists(args.savepath):
        if args.cpu_mode:
            caffe.set_mode_cpu()
        else:
            caffe.set_mode_gpu()
            caffe.set_device(args.gpu_id)
        caffe_net = caffe.Net(args.proto, args.net, caffe.TEST)

        pred_all_dets = {}
        n_fr = len(ucfsports_test.image_index)
        for i in range(n_fr):
            image_name = ucfsports_test.image_index[i]
            image_path = os.path.join(ucfsports_test._data_path, image_name)
            pred_all_dets[image_name] = action.detect_action_img(caffe_net, image_path, 0, LEN)
        with open(args.savepath,'w') as fid:
            pickle.dump(pred_all_dets, fid)
    else:
        with open(args.savepath,'r') as fid:
            pred_all_dets = pickle.load(fid)

#     ap_all = action.evaluate_frameAP(roidb, pred_all_dets, ucfsports_test._classes)
#     print ucfsports_test._classes[1:]
    # print ap_all
    # print 'mean frame AP: {}'.format(np.mean(np.array(ap_all)))

    # ==== video AP evaluation ====
    gt_video = ucfsports_test.get_test_video_annotations()
    ap_all = action.evaluate_videoAP(gt_video, pred_all_dets, ucfsports_test._classes, 0.75)
    print ucfsports_test._classes[1:]
    print ap_all
    print 'mean video AP: {}'.format(np.mean(np.array(ap_all)))

