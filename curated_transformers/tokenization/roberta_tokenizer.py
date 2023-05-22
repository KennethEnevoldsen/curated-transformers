from typing import Any, Iterable, List, Type, TypeVar
from cutlery import ByteBPEProcessor
import json
from pathlib import Path

from .bbpe_tokenizer import ByteBPETokenizer
from .hf_hub import FromPretrainedHFTokenizer
from .tokenizer import PiecesWithIds, PostEncoder, PreDecoder
from .util import remove_pieces_from_sequence, add_bos_eos_to_encoding


# Only provided as typing.Self in Python 3.11+.
Self = TypeVar("Self", bound="RobertaTokenizer")


class RobertaPreDecoder(PreDecoder):
    def __init__(
        self,
        *,
        bos_id: int,
        eos_id: int,
    ):
        """Construct a RoBERTa pre-decoder.

        bos_id (int): The piece id used to mark the beginning of a sequence.
        eos_id (int): The piece id used to mark the end of a sequence.
        """
        self.bos_id = bos_id
        self.eos_id = eos_id

    def __call__(self, input: Iterable[Iterable[int]]) -> List[List[int]]:
        return [
            list(remove_pieces_from_sequence(ids, (self.bos_id, self.eos_id)))
            for ids in input
        ]


class RobertaPostEncoder(PostEncoder):
    def __init__(
        self,
        *,
        bos_piece: str,
        eos_piece: str,
        bos_id: int,
        eos_id: int,
    ):
        """Construct a RoBERTa post-encoder.

        bos_piece (str): The piece used to mark the beginning of a sequence.
        eos_piece (str): The piece used to mark the end of a sequence.
        bos_id (int): The piece id used to mark the beginning of a sequence.
        eos_id (int): The piece id used to mark the end of a sequence.
        """
        self.bos_piece = bos_piece
        self.eos_piece = eos_piece
        self.bos_id = bos_id
        self.eos_id = eos_id

    def __call__(self, pieces_with_ids: PiecesWithIds) -> PiecesWithIds:
        return add_bos_eos_to_encoding(
            pieces_with_ids,
            bos_piece=self.bos_piece,
            eos_piece=self.eos_piece,
            bos_id=self.bos_id,
            eos_id=self.eos_id,
        )


class RobertaTokenizer(ByteBPETokenizer, FromPretrainedHFTokenizer):
    def __init__(
        self,
        *,
        processor: ByteBPEProcessor,
        bos_piece: str = "<s>",
        eos_piece: str = "</s>",
    ):
        """Construct a RoBERTa tokenizer from a cutlery byte-level BPE processor.

        processor (ByteBPEProcessor): The processor to wrap.
        bos_piece (str): The piece to use to mark the beginning of a sequence.
        eos_piece (str): The piece to use to mark the end of a sequence.
        """
        super().__init__(processor=processor)

        self.processor = processor

        bos_id = _get_piece_id_or_fail(processor, bos_piece)
        eos_id = _get_piece_id_or_fail(processor, eos_piece)

        self.pre_decoder = RobertaPreDecoder(
            bos_id=bos_id,
            eos_id=eos_id,
        )

        self.post_encoder = RobertaPostEncoder(
            bos_piece=bos_piece,
            eos_piece=eos_piece,
            bos_id=bos_id,
            eos_id=eos_id,
        )

    @classmethod
    def from_files(
        cls: Type[Self],
        *,
        vocab_path: Path,
        merges_path: Path,
        bos_piece: str = "<s>",
        eos_piece: str = "</s>",
    ) -> Self:
        """Construct a tokenizer from vocabulary and merge files.

        vocab_path (Path): path to the vocabulary file.
        merges_path (Path): path to the merges file.
        bos_piece (str): The piece to use to mark the beginning of a sequence.
        eos_piece (str): The piece to use to mark the end of a sequence.
        """
        processor = ByteBPEProcessor.load_from_files(
            vocab=vocab_path, merges=merges_path
        )
        return cls(
            processor=processor,
            bos_piece=bos_piece,
            eos_piece=eos_piece,
        )

    @classmethod
    def convert_hf_tokenizer(cls: Type[Self], tokenizer: Any) -> Self:
        serialized = tokenizer.backend_tokenizer.to_str(True)  # type: ignore
        deserialized = json.loads(serialized)
        vocab_merges = deserialized["model"]
        merges = [tuple(merge.split(" ")) for merge in vocab_merges["merges"]]
        processor = ByteBPEProcessor(vocab_merges["vocab"], merges)
        bos_piece = tokenizer.bos_token  # type: ignore
        eos_piece = tokenizer.eos_token  # type: ignore
        return cls(
            processor=processor,
            bos_piece=bos_piece,
            eos_piece=eos_piece,
        )


def _get_piece_id_or_fail(processor: ByteBPEProcessor, piece: str):
    piece_id = processor.piece_id(piece)
    if piece_id is None:
        raise ValueError(
            f"RoBERTa piece encoder vocabulary doesn't contain '{piece}' piece"
        )
    return piece_id