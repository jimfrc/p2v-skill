#!/usr/bin/env node
/**
 * Combine PNG/JPEG images into a multi-page PDF, one image per page.
 *
 * This is a cross-platform replacement for:
 *   magick out/scene1.png out/scene2.png ... out/slides.pdf
 * which requires ImageMagick to be installed (not the case on a stock Windows machine).
 *
 * Requires the `pdf-lib` package. Install it once in the Remotion project root:
 *   npm install pdf-lib
 *
 * Usage: node images-to-pdf.mjs <out.pdf> <image1.png> <image2.png> [...]
 */

import Fs from 'node:fs';
import Path from 'node:path';

const [outputPath, ...inputPaths] = process.argv.slice(2);

if (!outputPath || inputPaths.length === 0) {
	console.error('usage: node images-to-pdf.mjs <out.pdf> <image1.png> <image2.png> [...]');
	process.exit(1);
}

let PDFLib;
try {
	PDFLib = await import('pdf-lib');
} catch {
	console.error('error: the "pdf-lib" package is not installed.');
	console.error('Run `npm install pdf-lib` in the project root, then retry.');
	process.exit(1);
}

const pdf = await PDFLib.PDFDocument.create();

for (const inputPath of inputPaths) {
	const bytes = Fs.readFileSync(inputPath);
	const extension = Path.extname(inputPath).toLowerCase();
	const image = (extension === '.jpg' || extension === '.jpeg')
		? await pdf.embedJpg(bytes)
		: await pdf.embedPng(bytes);

	const page = pdf.addPage([image.width, image.height]);
	page.drawImage(image, { x: 0, y: 0, width: image.width, height: image.height });
}

await Fs.promises.mkdir(Path.dirname(Path.resolve(outputPath)), { recursive: true });
await Fs.promises.writeFile(outputPath, await pdf.save());

console.log(`Wrote ${outputPath} (${inputPaths.length} page${inputPaths.length === 1 ? '' : 's'})`);
