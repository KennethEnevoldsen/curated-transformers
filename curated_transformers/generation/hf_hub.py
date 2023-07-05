from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar

import torch

from ..quantization import BitsAndBytesConfig

# Only provided as typing.Self in Python 3.11+.
Self = TypeVar("Self", bound="FromHFHub")


class FromHFHub(ABC):
    @classmethod
    @abstractmethod
    def from_hf_hub(
        cls: Type[Self],
        *,
        name: str,
        revision: str = "main",
        device: Optional[torch.device] = None,
        quantization_config: Optional[BitsAndBytesConfig] = None,
    ) -> Self:
        """
        Construct a generator and load its parameters from Hugging Face Hub.

        :param name:
            Model name.
        :param revsion:
            Model revision.
        :param device:
            Device on which to initialize the model.
        :param quantization_config:
            Configuration for loading quantized weights.
        :returns:
            Generator with the parameters loaded.
        """
        ...