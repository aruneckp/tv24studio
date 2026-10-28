"""Neural Telugu newsreader voice — AI4Bharat Indic-TTS (FastPitch + HiFi-GAN), CPU only.

Besides the audio, it returns per-character timings from FastPitch's duration
predictor, which drive the anchor's lip sync exactly (no guessing from loudness).

    from .tts_te import TeluguVoice
    v = TeluguVoice()
    wav, sr, chars = v.say("నమస్కారం.", speaker="male")
    # chars = [(char, start_sec, end_sec), ...]
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import torch

from .. import config

# Model files are downloaded data: only ever unpickle plain tensors/containers,
# never arbitrary objects, whatever a library asks for.
_torch_load = torch.load


def _weights_only_load(*args, **kwargs):
    kwargs["weights_only"] = True
    return _torch_load(*args, **kwargs)


torch.load = _weights_only_load


class TeluguVoice:
    def __init__(self, model_dir: str | None = None, threads: int = 2):
        model_dir = model_dir or os.environ.get("TV24_TE_MODEL", str(config.BASE_DIR / "models/te"))
        from TTS.utils.synthesizer import Synthesizer

        torch.set_num_threads(threads)
        d = Path(model_dir)
        if not (d / "fastpitch/best_model.pth").exists():
            raise FileNotFoundError(
                f"Telugu voice model not found at {d}. Download it with:\n"
                "  curl -L -o models/te.zip "
                "https://github.com/AI4Bharat/Indic-TTS/releases/download/v1-checkpoints-release/te.zip\n"
                "  unzip -q models/te.zip -d models && rm models/te.zip"
            )
        # the released config points at the authors' training paths; patch a copy
        cfg = json.loads((d / "fastpitch/config.json").read_text())
        spk = str(d / "fastpitch/speakers.pth")
        cfg["speakers_file"] = spk
        cfg["model_args"]["speakers_file"] = spk
        cfg_path = config.BASE_DIR / "models" / "_fastpitch_config.json"
        cfg_path.parent.mkdir(exist_ok=True)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False))
        self.syn = Synthesizer(
            tts_checkpoint=str(d / "fastpitch/best_model.pth"),
            tts_config_path=str(cfg_path),
            tts_speakers_file=str(d / "fastpitch/speakers.pth"),
            vocoder_checkpoint=str(d / "hifigan/best_model.pth"),
            vocoder_config=str(d / "hifigan/config.json"),
            use_cuda=False,
        )
        self.model = self.syn.tts_model
        self.sr = self.syn.output_sample_rate
        self.hop = self.syn.tts_config.audio["hop_length"]
        self.mel_sr = self.syn.tts_config.audio["sample_rate"]
        self.speakers = list(self.model.speaker_manager.name_to_id)

    @torch.inference_mode()
    def say(self, text: str, speaker: str = "male", pace: float = 1.0):
        """pace > 1 speaks faster. Returns (float32 wav, sr, [(char, t0, t1)])."""
        m = self.model
        m.length_scale = 1.0 / pace
        ids = m.tokenizer.text_to_ids(text)
        x = torch.LongTensor(ids)[None]
        sid = torch.LongTensor([m.speaker_manager.name_to_id[speaker]])
        out = m.inference(x, aux_input={"speaker_ids": sid, "d_vectors": None})
        mel = out["model_outputs"]  # [1, T, C]
        dlog = out["durations_log"].reshape(-1).float()
        dur = torch.clamp(torch.round((torch.exp(dlog) - 1) * m.length_scale), min=1).numpy()  # frames/token
        # vocoder (same normalisation path the Synthesizer uses)
        mel_np = mel[0].numpy().T
        mel_np = self.syn.tts_model.ap.denormalize(mel_np)
        vmel = self.syn.vocoder_ap.normalize(mel_np)
        vin = torch.tensor(vmel)[None].float()
        wav = self.syn.vocoder_model.inference(vin)[0, 0].numpy().astype(np.float32)
        # token -> time
        fr = self.hop / self.mel_sr
        ends = np.cumsum(np.round(dur)) * fr
        starts = np.concatenate([[0], ends[:-1]])
        chars = []
        for tid, s, e in zip(ids, starts, ends):
            ch = m.tokenizer.characters.id_to_char(tid)
            if ch in ("<BLNK>", "<PAD>", "<BOS>", "<EOS>"):
                continue
            chars.append((ch, float(s), float(e)))
        return wav, self.sr, chars
