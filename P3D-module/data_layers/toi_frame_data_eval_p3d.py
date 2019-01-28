'''
The Caffe data layer for training label classifier.
This layer will parse pixel values and actionness labels to the network.
'''
import sys
sys.path.insert(0, '/data/wjc/TCNN_STCNN/caffe/python')
#sys.path.insert(0, '/home/rhou/caffe/python')
import caffe
from dataset.jhmdb import jhmdb
import numpy as np
from utils.cython_bbox import bbox_overlaps
from utils.bbox_transform import bbox_transform_inv

class RegDataLayer():
  def __init__(self, net, model):
    self._batch_size = 1
    self._depth = 8
    self._height = 300
    self._width = 400
    self.dataset = jhmdb('val', [self._height, self._width],
                             split=1)
    self.top = 40

    self.anchors, self.valid_idx, self._anchor_dims = self.dataset.get_anchors()

    caffe.set_mode_gpu()
    self._net = caffe.Net(net, model, caffe.TEST)

  def forward(self, results):
    self._net.blobs['data'].reshape(self._batch_size, 3,
                                    self._depth, self._height, self._width)
    self._net.blobs['tois'].reshape(self._batch_size * self.top * 8, 5)
    self._net.blobs['toi2'].reshape(self._batch_size * self.top * 8, 5)

    [clip, gt_bboxes, labels, all_pred, _, is_last] = self.dataset.next_val_video()
    labels = int(labels)
    n = int(clip.shape[0])

    rrrrr = []
    for i in xrange(n - self._depth + 1):
      batch_clip = clip[i : i + 1* self._depth].transpose([3, 0, 1, 2])
      batch_clip = np.expand_dims(batch_clip, axis=0)

      pred = all_pred[i : i + 1* self._depth]
      pred_anchors = np.reshape(pred, (-1,4)) * 1.25
      curr_results = results[i]
      r1 = curr_results[:, :22]
      r2 = curr_results[:, 22:]
      curr_dets = {
        'boxes': np.empty((0, self._depth, 4)),
        'pred_label': np.empty((0)),
        'pred_scores': np.empty((0,2)),
        'label_length': np.empty((0)),
      }
      tmp = r1.argmax(axis=1)
      for j in xrange(1, self.dataset._num_classes):
        ttmp = tmp[tmp == j]
        if ttmp.size > 0:
          print ('pred_labe')
          print j
        argsort_r = np.argsort(r1[:, j])[-self.top:]
        curr_scores = np.vstack((r1[argsort_r, j], r2[argsort_r, j])).transpose()
        curr_boxes = pred_anchors[argsort_r]
        curr_boxes = np.repeat(curr_boxes, 8, axis=0)
        batch_tois = np.hstack((np.zeros((curr_boxes.shape[0], 1)),
                                curr_boxes))
        curr_idx = np.arange(self._depth).reshape(1, self._depth)
        curr_idx = np.repeat(curr_idx, self.top, axis=0).reshape(-1, 1)
        batch_toi2 = np.hstack((curr_idx, curr_boxes))

        self._net.blobs['data'].data[...] = batch_clip.astype(np.float32,
                                                              copy=False)
        self._net.blobs['tois'].data[...] = batch_tois.astype(np.float32,
                                                              copy=False)
        self._net.blobs['toi2'].data[...] = batch_toi2.astype(np.float32,
                                                              copy=False)

        self._net.forward()

        diff = self._net.blobs['fc8-2'].data[...][:, (j - 1) * 4 : j * 4]
       
        #print ('hhahaha')
        #print self._net.blobs['fc8-2'].data[...][:,:]
        #print self._net.blobs['fc8-2'].data[...][40,:] 
#        diff[:,0:2] = np.maximum(-0.3, np.minimum(0.3, diff[:,0:2]))
#        diff[:,2:4] = np.maximum(-0.5, np.minimum(0.5, diff[:,2:4]))

        boxes = bbox_transform_inv(batch_tois[:, 1 : 5], diff).reshape((self.top, 8, 4)) * 16
        
        boxes[:,:,0::2] = np.maximum(0, np.minimum(398.75, boxes[:,:,0::2]))
        boxes[:,:,1::2] = np.maximum(0, np.minimum(298.75, boxes[:,:,1::2]))

        
        curr_dets['boxes'] = np.vstack((curr_dets['boxes'], boxes))
        curr_dets['pred_label'] = np.hstack((curr_dets['pred_label'], np.ones(self.top) * j))
        curr_dets['pred_scores'] = np.vstack((curr_dets['pred_scores'], curr_scores))
        curr_dets['label_length'] = np.hstack((curr_dets['label_length'], ttmp.size))

      rrrrr.append(curr_dets)

    r = {'dets': rrrrr,
         'gt_bboxes': gt_bboxes,
         'gt_label': labels}
    '''
      stack_overlaps = np.empty((self._depth, self.top, gt_bboxes.shape[0]))
      for j in xrange(self._depth):
        curr_gt_idx = np.where(gt_bboxes[0,:,0] == i * self._depth + j)[0]
        curr_gt = gt_bboxes[:, curr_gt_idx, 1 : 5].reshape(-1, 4)
        overlaps = bbox_overlaps(
          np.ascontiguousarray(boxes[:, j], dtype=np.float),
          np.ascontiguousarray(curr_gt, dtype=np.float))
        stack_overlaps[j] = overlaps

        # Find wrong detections.

      for j in xrange(stack_overlaps.shape[2]):
        argmax_overlaps = np.sum(stack_overlaps[:,:,j], axis=0).argmax()
        ov[i * self._depth : (i+1) * self._depth, j] = stack_overlaps[:, argmax_overlaps, j]
    '''
    return is_last, r

