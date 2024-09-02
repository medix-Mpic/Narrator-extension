import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
# USE CUDA FOR A MUCH FASTER PERFORMANCE
# GPU supports streaming while CPU doesn't 