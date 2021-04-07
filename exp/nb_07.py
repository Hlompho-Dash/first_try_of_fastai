
#################################################
### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
#################################################
# file to edit: dev_nb/07_batchNorm.ipynb
import os
os.chdir('/content/gdrive/MyDrive/first_try_of_fastai/exp')
from nb_06 import *
os.chdir('/content/gdrive/MyDrive/first_try_of_fastai')

def init_cnn_(m,f):
  if isinstance(m, nn.Conv2d):
    f(m.weight, a=0.1)
    if getattr(m, 'bias',None) is not None: m.bias.data.zero_()
  for l in m.children(): init_cnn_(l, f)

def init_cnn(m, uniform=False):
  f = init.kaiming_uniform_ if uniform else init.kaiming_normal_
  init_cnn_(m,f)

def get_learn_run(nfs, data, lr, layer, cbs=None, opt_func=None, uniform=False, **kwargs):
  model = get_cnn_model(data, nfs, layer, **kwargs)
  init_cnn(model, uniform=uniform)
  return get_runner(model, data, lr=lr, cbs=cbs, opt_func=opt_func)

def append_stats(i, mod, inp, outp):
  act_means[i].append(outp.data.mean())
  act_stds [i].append(outp.data.std())

def children(m): return list(m.children())

class Hook():
  def __init__(self, m, f): self.hook = m.register_forward_hook(partial(f, self))
  def remove(self): self.hook.remove()
  def __del__(self): self.remove()

def append_stats(hook, mod, inp, outp):
  if not hasattr(hook,'stats'): hook.stats = ([],[])
  means, stds = hook.stats
  means.append(outp.data.mean())
  stds.append(outp.data.std())

class ParamScheduler(Callback):
  _order = 1
  def __init__(self, pname, sched_func):
    self.pname, self.sched_func = pname, sched_func

  def set_param(self):
    for pg in self.opt.param_groups:
      pg[self.pname] = self.sched_func(self.n_epochs/self.epochs)

  def begin_batch(self):
    if self.in_train: self.set_param()

def conv_layer(ni, nf, ks=3, stride=2, bn=True, **kwargs):
  layers = [nn.Conv2d(ni,nf,ks,padding=ks//2,stride=stride,bias=not bn),
            GeneralRelu(**kwargs)]
  if bn: layers.append(nn.BatchNorm2d(nf, eps=1e-5, momentum=0.1))
  return nn.Sequential(*layers)

#export
class RunningBatchNorm(nn.Module):
  def __init__(self, nf, mom=0.1, eps=1e-5):
    super().__init__()
    self.mom, self.eps = mom,eps
    self.mults = nn.Parameter(torch.one(nf,1,1))
    self.adds = nn.Parameter(torch.zeros(nf,1,1))
    self.register_buufer('sums', torch.zeros(1,nf,1,1))
    self.register_buufer('sqrs', torch.zeros(1,nf,1,1))
    self.register_buufer('count', tensor(0.))
    self.register_buufer('factor', tensor(0.))
    self.register_buufer('offset', tensor(0.))
    self.batch = 0

  def update_stats(self, x):
    bs,nc,*_ = x.shape
    self.sums.detach_()
    self.sqrs.detach_()
    dims = (0,2,3)
    s = x.sum(dims, keepdim=True)
    ss = (x*x).sum(dims, keepdim=True)
    c = s.new_tensor(x.numel()/nc)
    mom1 = s.new_tensor(1 - (1-self.mom) / math.sqrt(bs-1))
    self.sums.lerp_(s, mom1)
    self.sqrs.lerp_(ss, mom1)
    self.count.lerp_(c, mom1)
    self.batch += bs
    means = self.sums/self.count
    varns = (self.sqrs/self.count).sub_(means*means)
    if bool(self.batch < 20): vars.clamp_min_(0.01)
    self.factor = self.mults / (varns+self.eps).sqrt()
    self.offset = seslf.adds - means*self.factor

  def forward(self, x):
    if self.training: self.update_stats(x)
    return x*self.factor + self.offset