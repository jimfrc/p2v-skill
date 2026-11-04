#!/usr/bin/env node
/**
 * Print the duration of a WAV file in seconds (3 decimals).
 *
 * This is a dependency-free replacement for:
 *   ffprobe -v error -show_entries format=duration -of csv=p=0 <file>
 * which is not available on a stock Windows machine.
 *
 * Usage: node wav-duration.mjs <file.wav>
 */

import Fs from 'node:fs';

const file = process.argv[2];
if (!file) {
	console.error('usage: node wav-duration.mjs <file.wav>');
	process.exit(1);
}

const buffer = Fs.readFileSync(file);
if (buffer.length < 12 || buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WAVE') {
	console.error(`error: not a WAV file: ${file}`);
	process.exit(1);
}

let byteRate = 0;
let dataSize = 0;
let offset = 12;

while (offset + 8 <= buffer.length) {
	const chunkId = buffer.toString('ascii', offset, offset + 4);
	const chunkSize = buffer.readUInt32LE(offset + 4);

	if (chunkId === 'fmt ' && offset + 20 <= buffer.length) {
		byteRate = buffer.readUInt32LE(offset + 16);
	} else if (chunkId === 'data') {
		// Some encoders write a bogus size; clamp it to what is actually in the file.
		dataSize = Math.min(chunkSize, buffer.length - offset - 8);
		break;
	}

	offset += 8 + chunkSize + (chunkSize % 2);
}

if (byteRate === 0) {
	console.error(`error: could not find a "fmt " chunk in ${file}`);
	process.exit(1);
}

console.log((dataSize / byteRate).toFixed(3));
