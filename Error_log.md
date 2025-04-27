## 2025.2.23
AttributeError: 'Upsample' object has no attribute 'recompute_scale_factor'
解决方法: 换了conda环境不报错，不知道什么原因，重装torch还是不行，最后删了Upsampling.py的"recompute_scale_factor=self.recompute_scale_factor"（查了下可以运行的环境确实也没这个）

