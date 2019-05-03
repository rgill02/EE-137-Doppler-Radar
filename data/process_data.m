%Cleanup
close all;
clear;
clc;

%Load data
load('car.mat');

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
fc = 10.525e9;
c = 3e8;
v = f * c / 2 / fc;

%Create a high pass filter
high_pass_cutoff = 100;
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
H_chunks = fftshift(fft(chunks .* hamming(chunk_size)', nfft, 2), 2);
H_chunks_filt = H_chunks .* high_pass;
chunks_filt = ifft(ifftshift(H_chunks_filt, 2), [], 2);
chunks_filt = chunks_filt(:,1:chunk_size) ./ hamming(chunk_size)';

%Bring to frequency domain with taper to analyze
%H_chunks = fftshift(fft(chunks .* hamming(chunk_size)', nfft, 2), 2);

%Plot
figure;
imagesc(t * 1e3, [], chunks_filt);
xlabel('Time (ms)');
ylabel('Chunk Number');
title('Time Domain');
h = colorbar;
ylabel(h, 'Volts');

figure;
imagesc(v, [], abs(H_chunks_filt));
xlabel('Veloctiy (m/s)');
ylabel('Chunk Number');
title('Frequency Domain');
xlim([0, max(v)]);
h = colorbar;
ylabel(h, 'Magnitude (Count)');

figure;
imagesc(v, [], 20*log10(abs(H_chunks_filt)));
xlabel('Veloctiy (m/s)');
ylabel('Chunk Number');
title('Frequency Domain');
xlim([0, max(v)]);
h = colorbar;
ylabel(h, 'Magnitude (Log)');
