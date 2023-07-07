from abc import ABC, abstractmethod
from typing import Generic, Mapping, Optional, Type, TypeVar

import torch

from curated_transformers.models.llama.decoder import LLaMADecoder

from ..models.albert import AlbertEncoder
from ..models.bert import BertEncoder
from ..models.camembert import CamembertEncoder
from ..models.gpt_neox import GPTNeoXCausalLM, GPTNeoXDecoder
from ..models.hf_hub import FromPretrainedHFModel
from ..models.llama import LLaMACausalLM
from ..models.module import CausalLMModule, DecoderModule, EncoderModule
from ..models.output import KeyValueCache
from ..models.refined_web_model import RefinedWebModelCausalLM, RefinedWebModelDecoder
from ..models.roberta import RobertaEncoder
from ..models.xlm_roberta import XlmRobertaEncoder
from ..quantization import BitsAndBytesConfig
from ..util.hf import get_hf_config_model_type

ModelT = TypeVar("ModelT")


class AutoModel(ABC, Generic[ModelT]):
    """Base class for models that can be loaded from the Hugging
    Face Model Hub."""

    @classmethod
    @abstractmethod
    def from_hf_hub(
        cls,
        name: str,
        revision: str = "main",
        *,
        device: Optional[torch.device] = None,
        quantization_config: Optional[BitsAndBytesConfig] = None,
    ) -> ModelT:
        """Construct and load a module or a generator from Hugging Face Hub.

        :param name:
            Model name.
        :param revsion:
            Model revision.
        :param device:
            Device on which to initialize the model.
        :param quantization_config:
            Configuration for loading quantized weights.
        :returns:
            Loaded module or generator.
        """
        raise NotImplementedError

    @classmethod
    def _instantiate_module_from_hf_hub(
        cls,
        name: str,
        revision: str,
        device: Optional[torch.device],
        quantization_config: Optional[BitsAndBytesConfig],
        model_type_to_class_map: Mapping[str, Type],
    ) -> FromPretrainedHFModel:
        model_type = get_hf_config_model_type(name, revision)
        module_cls = model_type_to_class_map.get(model_type)
        if module_cls is None:
            raise ValueError(
                f"Unsupported model type `{model_type}` for {cls.__name__}. "
                f"Supported model types: {tuple(model_type_to_class_map.keys())}"
            )
        assert issubclass(module_cls, FromPretrainedHFModel)
        module = module_cls.from_hf_hub(
            name, revision, device=device, quantization_config=quantization_config
        )
        return module


class AutoEncoder(AutoModel[EncoderModule]):
    """Encoder module loaded from the Hugging Face Model Hub."""

    _HF_MODEL_TYPE_TO_CURATED = {
        "bert": BertEncoder,
        "albert": AlbertEncoder,
        "camembert": CamembertEncoder,
        "roberta": RobertaEncoder,
        "xlm-roberta": XlmRobertaEncoder,
    }

    @classmethod
    def from_hf_hub(
        cls,
        name: str,
        revision: str = "main",
        *,
        device: Optional[torch.device] = None,
        quantization_config: Optional[BitsAndBytesConfig] = None,
    ) -> EncoderModule:
        encoder = cls._instantiate_module_from_hf_hub(
            name, revision, device, quantization_config, cls._HF_MODEL_TYPE_TO_CURATED
        )
        assert isinstance(encoder, EncoderModule)
        return encoder


class AutoDecoder(AutoModel[DecoderModule]):
    """Decoder module loaded from the Hugging Face Model Hub."""

    _HF_MODEL_TYPE_TO_CURATED = {
        "gpt_neox": GPTNeoXDecoder,
        "llama": LLaMADecoder,
        "RefinedWeb": RefinedWebModelDecoder,
        "RefinedWebModel": RefinedWebModelDecoder,
    }

    @classmethod
    def from_hf_hub(
        cls,
        name: str,
        revision: str = "main",
        *,
        device: Optional[torch.device] = None,
        quantization_config: Optional[BitsAndBytesConfig] = None,
    ) -> DecoderModule:
        decoder = cls._instantiate_module_from_hf_hub(
            name, revision, device, quantization_config, cls._HF_MODEL_TYPE_TO_CURATED
        )
        assert isinstance(decoder, DecoderModule)
        return decoder


class AutoCausalLM(AutoModel[CausalLMModule[KeyValueCache]]):
    """Causal LM module loaded from the Hugging Face Model Hub."""

    _HF_MODEL_TYPE_TO_CURATED = {
        "gpt_neox": GPTNeoXCausalLM,
        "llama": LLaMACausalLM,
        "RefinedWeb": RefinedWebModelCausalLM,
        "RefinedWebModel": RefinedWebModelCausalLM,
    }

    @classmethod
    def from_hf_hub(
        cls,
        name: str,
        revision: str = "main",
        *,
        device: Optional[torch.device] = None,
        quantization_config: Optional[BitsAndBytesConfig] = None,
    ) -> CausalLMModule[KeyValueCache]:
        causal_lm = cls._instantiate_module_from_hf_hub(
            name, revision, device, quantization_config, cls._HF_MODEL_TYPE_TO_CURATED
        )
        assert isinstance(causal_lm, CausalLMModule)
        return causal_lm
