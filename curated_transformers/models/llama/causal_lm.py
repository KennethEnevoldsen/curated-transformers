from typing import Any, List, Mapping, Optional, Set, Type, TypeVar

import torch
from torch import Tensor
from torch.nn import Linear

from ...quantization import Quantizable
from ..attention import AttentionMask
from ..hf_hub import FromPretrainedHFModel
from ..module import CausalLMModule
from ..output import CausalLMOutputWithCache, KeyValueCache
from ._hf import convert_hf_config, convert_hf_state_dict
from .config import LLaMAConfig
from .decoder import LLaMADecoder

# Only provided as typing.Self in Python 3.11+.
Self = TypeVar("Self", bound="LLaMACausalLM")


class LLaMACausalLM(CausalLMModule[KeyValueCache], FromPretrainedHFModel, Quantizable):
    """
    LLaMa (Touvron et al., 2023) causal language model.
    """

    def __init__(
        self, config: LLaMAConfig, *, device: Optional[torch.device] = None
    ) -> None:
        super().__init__()

        self.decoder = LLaMADecoder(config, device=device)
        self.output_embeddings = Linear(
            in_features=config.layer.hidden_width,
            out_features=config.embedding.vocab_size,
            bias=False,
            device=device,
        )

    def forward(
        self,
        input_ids: Tensor,
        attention_mask: Optional[AttentionMask] = None,
        cache: Optional[List[KeyValueCache]] = None,
        positions: Optional[Tensor] = None,
        store_cache: bool = False,
    ) -> CausalLMOutputWithCache[KeyValueCache]:
        decoder_output = self.decoder(
            input_ids,
            attention_mask,
            cache=cache,
            store_cache=store_cache,
            positions=positions,
        )
        logits = self.output_embeddings(decoder_output.last_hidden_layer_states)

        return CausalLMOutputWithCache(
            cache=decoder_output.cache,
            embedding_output=decoder_output.embedding_layer,
            layer_hidden_states=decoder_output.all_hidden_layer_states,
            logits=logits,
        )

    @classmethod
    def convert_hf_state_dict(cls, params: Mapping[str, Tensor]):
        return convert_hf_state_dict(cls, params)

    @classmethod
    def from_hf_config(
        cls: Type[Self],
        *,
        hf_config: Any,
        device: Optional[torch.device] = None,
    ) -> Self:
        config = convert_hf_config(hf_config)
        return cls(config, device=device)

    @classmethod
    def modules_to_not_quantize(cls) -> Set[str]:
        # Ignore the LM output embedding matrix.
        return {"output_embeddings"}