%Cleanup
close all;
clear;
clc;

%Load data
load('metal_board_test_with_300_gain.mat');

%Convert to matlab doubles
chunk_size = double(chunk_size);
data = double(data);
ts_us = double(ts_us);

%Compute other values
Ts = ts_us / 1e6;
fs = 1 / Ts;
nfft = 2^(nextpow2(chunk_size) + 2);
f = (-nfft/2:nfft/2-1)*(fs/nfft);
t = 0:Ts:Ts*chunk_size-Ts;

%Create a high pass filter
high_pass_cutoff = 1;
idxs = (f >= -high_pass_cutoff) & (f <= high_pass_cutoff);
high_pass = ones(1, nfft);
high_pass(idxs) = 0;

% figure;
% plot(f, high_pass);
% xlabel('Frequency (Hz)');
% ylabel('Amplitude');
% title('High Pass Filter');

%Reshape signal into chunks to process and bring to frequency domain and
%apply high pass filter
chunks = reshape(data, chunk_size, [])';
H_chunks = fftshift(fft(chunks, nfft, 2), 2);
H_chunks_filt = H_chunks .* high_pass;
chunks_filt = ifft(ifftshift(H_chunks_filt, 2), [], 2);
chunks = chunks_filt(:,1:chunk_size);

%Bring to frequency domain with taper to analyze
H_chunks = fftshift(fft(chunks .* hamming(chunk_size)', nfft, 2), 2);

%Plot
figure;
imagesc(t * 1e3, [], chunks);
xlabel('Time (ms)');
ylabel('Chunk Number');
title('Time Domain');
h = colorbar;
ylabel(h, 'Volts');

figure;
imagesc(f, [], abs(H_chunks));
xlabel('Frequency (Hz)');
ylabel('Chunk Number');
title('Frequency Domain');
xlim([0, max(f)]);
h = colorbar;
ylabel(h, 'Magnitude (Count)');

figure;
imagesc(f, [], 20*log10(abs(H_chunks)));
xlabel('Frequency (Hz)');
ylabel('Chunk Number');
title('Frequency Domain');
xlim([0, max(f)]);
h = colorbar;
ylabel(h, 'Magnitude (Log)');
