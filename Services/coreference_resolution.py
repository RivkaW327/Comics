import sys
from config.config_loader import config

sys.path.append(config["services"]["maverick_coref"]["path"])

from .maverick_coref.maverick import Maverick
import torch

coref_model = Maverick(
  hf_name_or_path= config["services"]["maverick_coref"]["weights"],
  device="cpu" if not torch.cuda.is_available() else "cuda:0"
)
def load_coref_model():
    return coref_model