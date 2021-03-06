import argparse
import os

import numpy as np

from config import CHECKPOINT_DIR, DEFAULT_SAMPLING_RATE, IMG_DIM, OUTPUT_PATH
from data import (amplitude_to_db, db_to_amplitude, forward_transform,
                  init_directory, inverse_transform, join_magnitude_slices,
                  load_audio, slice_magnitude, write_audio)
from model import Generator

def predict_multitarget(model, input_filename, style_filename, output_filename):
    # Load melody
    audio = load_audio(input_filename, sr=DEFAULT_SAMPLING_RATE)
    mag, phase = forward_transform(audio)
    mag_db = amplitude_to_db(mag)
    mag_sliced = slice_magnitude(mag_db, IMG_DIM[1])
    mag_sliced = (mag_sliced * 2) - 1

    # Load style
    style = load_audio(style_filename, sr=DEFAULT_SAMPLING_RATE)
    style_mag, _ = forward_transform(style)
    style_mag_db = amplitude_to_db(style_mag)
    style_mag_sliced = slice_magnitude(style_mag_db, IMG_DIM[1])
    
    # Take a random slice
    style_mag_sliced = style_mag_sliced[np.random.choice(style_mag_sliced.shape[0]),:,:]
    style_mag_sliced = (style_mag_sliced * 2) - 1
    style_mag_sliced = np.expand_dims(style_mag_sliced, axis=0)
    style_mag_sliced = np.repeat(style_mag_sliced, mag_sliced.shape[0], axis=0)

    # Concatenate [melody, style]
    input_data = np.concatenate([mag_sliced, style_mag_sliced], axis=3)
    prediction = model.predict(input_data)
    prediction = (prediction + 1) / 2

    mag_db = join_magnitude_slices(prediction, phase.shape)
    mag = db_to_amplitude(mag_db)
    audio_out = inverse_transform(mag, phase)
    write_audio(output_filename, audio_out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', required=True)
    ap.add_argument('--input', required=True)
    ap.add_argument('--style', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    assert os.path.isfile(args.model), 'Model not found'
    assert os.path.isfile(args.input), 'Input audio not found'
    assert os.path.isfile(args.style), 'Style not found'
    
    _, ext = os.path.splitext(args.input)
    assert ext in ['.wav', '.mp3', '.ogg'], 'Invalid audio format'

    # Enable mixed precision
    os.environ['TF_ENABLE_AUTO_MIXED_PRECISION'] = '1'

    model = Generator(input_shape=[None,None,2])
    model.load_weights(args.model)
    print('Weights loaded from', args.model)

    base_output_path, _ = os.path.split(args.output)
    init_directory(base_output_path)
    print('Created directory', base_output_path)
    
    predict_multitarget(model, args.input, args.style, args.output)
    print('Prediction saved in', args.output)