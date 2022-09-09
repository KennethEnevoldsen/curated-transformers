from dataclasses import dataclass
from typing import Optional, Tuple, List

import torch
from torch.nn import Module
from torch import Tensor

from .components import EncoderLayer, SinusoidalPositionalEmbedding


@dataclass
class TransformerEncoderOutput:
    layer_outputs: List[Tensor]  # [batch, seq, model_hidden]
    embedding_sum: Tensor  # [batch, seq, emb_dim]

    @property
    def last_hidden_output(self) -> Tensor:
        return self.layer_outputs[len(self.layer_outputs) - 1]


class TransformerEncoder(Module):
    def __init__(
        self,
        hidden_size: int,
        intermediate_size: int,
        n_heads: int,
        n_layers: int,
        attn_dropout: float,
        hidden_dropout: float,
        hidden_activation: str,
        max_pos_embeddings: int,
        vocab_size: int,
        max_seq_len: int,
        *,
        learnable_pos_embeddings=False,
        layer_norm_eps: float = 1e-5,
        padding_idx: int = 0,
        type_vocab_size: int = 0,
    ):
        super().__init__()

        self.input_embeddings = torch.nn.Embedding(
            vocab_size, hidden_size, padding_idx=padding_idx
        )
        self.padding_idx = padding_idx
        self.max_seq_len = max_seq_len
        self.learnable_pos_embeddings = learnable_pos_embeddings

        if learnable_pos_embeddings:
            self.pos_embeddings = torch.nn.Embedding(num_embeddings=max_pos_embeddings, embedding_dim=hidden_size)  # type: ignore
        else:
            self.pos_embeddings = SinusoidalPositionalEmbedding(hidden_size, max_pos_embeddings)  # type: ignore

        if type_vocab_size > 0:
            self.token_type_embeddings = torch.nn.Embedding(num_embeddings=type_vocab_size, embedding_dim=hidden_size)  # type: ignore
        else:
            self.token_type_embeddings = None

        self.emb_layer_norm = torch.nn.LayerNorm(hidden_size, eps=layer_norm_eps)
        self.emb_dropout = torch.nn.Dropout(p=hidden_dropout)
        self.layers = torch.nn.ModuleList(
            [
                EncoderLayer(
                    hidden_size,
                    intermediate_size,
                    n_heads,
                    activation=hidden_activation,
                    attn_dropout=attn_dropout,
                    hidden_dropout=hidden_dropout,
                    layer_norm_eps=layer_norm_eps,
                )
                for _ in range(n_layers)
            ]
        )

    def _create_attention_mask(self, x: Tensor) -> Tensor:
        return x.ne(self.padding_idx).int()

    def _get_pos_embeddings(self, x: Tensor) -> Tensor:
        if self.learnable_pos_embeddings:
            # We need to generate the position IDs from the
            # input tensor to pass to the embedding layer and
            # handle padding, c.f https://github.com/huggingface/transformers/blob/330247ede2d8265aae9ab0b7a0d1a811c344960d/src/transformers/models/roberta/modeling_roberta.py#L1566

            mask = x.ne(self.padding_idx).int()
            pos_ids = (mask.cumsum(dim=1) * mask) + self.padding_idx
            return self.pos_embeddings(pos_ids)
        else:
            return self.pos_embeddings(x)

    def forward(
        self,
        input: Tensor,
        attention_mask: Optional[Tensor] = None,
        token_type_ids: Optional[Tensor] = None,
    ) -> TransformerEncoderOutput:
        """
        Shapes:
            input, token_type_ids - (batch, seq_len)

        `attn_mask` indicates elements to attend to with `1` (and `0` otherwise)

        Returns a tuple of consisting of a list of tensors from each Transformer
        layer and the sum of the input and positional embeddings.
        """
        if attention_mask is None:
            attention_mask = self._create_attention_mask(input)

        emb = self.input_embeddings(input)

        if self.token_type_embeddings is not None:
            if token_type_ids is None:
                token_type_ids = torch.zeros(
                    input.shape, dtype=torch.long, device=input.device
                )
            emb += self.token_type_embeddings(token_type_ids)

        pos = self._get_pos_embeddings(input)

        embedding_sum = emb + pos
        embedding_sum = self.emb_layer_norm(embedding_sum)
        embedding_sum = self.emb_dropout(embedding_sum)
        layer_output = embedding_sum

        layer_outputs = []
        for layer in self.layers:
            layer_output = layer(layer_output, attention_mask)
            layer_outputs.append(layer_output)

        return TransformerEncoderOutput(
            layer_outputs=layer_outputs, embedding_sum=embedding_sum
        )