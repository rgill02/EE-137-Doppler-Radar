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
v_mph = v / 0.44704;

%Reshape signal into chunks to process
chunks = reshape(data, chunk_size, [])';
%Remove dc component
ac_chunks = chunks - mean(chunks, 2);

%Plot time domain with dc component removed
figure;
imagesc(t * 1e3, [], ac_chunks);
xlabel('Time (ms)');
ylabel('Chunk Number');
title('Time Domain');
h = colorbar;
ylabel(h, 'Volts');

%Bring to frequency domain with taper
H_chunks = fftshift(fft(ac_chunks .* hamming(chunk_size)', nfft, 2), 2);

%Create a high pass filter
high_pass_cutoff_mph = 6;
high_pass_cutoff = 2 * high_pass_cutoff_mph * 0.44704 * fc / c;
idxs = (f >= -high_pass_cutoff) & (f <= high_pass_cutoff);
high_pass = ones(1, nfft);
high_pass(idxs) = 0;

%Apply high pass filter
H_chunks = H_chunks .* high_pass;

%Plot linear frequency domain
figure;
imagesc(v_mph, [], abs(H_chunks));
xlabel('Veloctiy (mph)');
ylabel('Chunk Number');
title('Frequency Domain');
xlim([0, max(v_mph)]);
h = colorbar;
ylabel(h, 'Magnitude (Count)');

%Plot log frequency domain
figure;
imagesc(v_mph, [], 20*log10(abs(H_chunks)));
xlabel('Veloctiy (mph)');
ylabel('Chunk Number');
title('Frequency Domain');
xlim([0, max(v_mph)]);
h = colorbar;
ylabel(h, 'Magnitude (dB)');

%Compute the energy in each chunk
engs = sum(abs(ac_chunks) .^ 2, 2);

%Plot energy in chunks
figure;
plot(engs);
xlabel('Chunk Number');
ylabel('Energy (Joules)');
title('Energy of Chunks');

%Find chunks with a target
detected_chunks = [];
thresh = 0.2070;
for ii = 1:length(engs)
    if engs(ii) > thresh
        detected_chunks = [detected_chunks; ii];
    end
end

%Plot detections
detects_to_plot = zeros(size(engs));
detects_to_plot(detected_chunks) = 1;
figure;
plot(detects_to_plot);
xlabel('Chunk Number');
ylabel('Detection (bool)');
title('Detected Chunks');

%Compute the moving average energy of chunks
smooth_engs = smoothdata(engs, 'movmean', 3);

%Plot smoothed energy in chunks
figure;
plot(smooth_engs);
xlabel('Chunk Number');
ylabel('Energy (Joules)');
title('Smoothed Energy of Chunks');

%Find chunks with a target
smooth_detected_chunks = [];
smooth_thresh = 0.17;
for ii = 1:length(smooth_engs)
    if smooth_engs(ii) > smooth_thresh
        smooth_detected_chunks = [smooth_detected_chunks; ii];
    end
end
for ii = 2:length(smooth_engs)-1
    if (smooth_engs(ii) <= smooth_thresh) && (smooth_engs(ii-1) > smooth_thresh) && (smooth_engs(ii+1) > smooth_thresh)
        smooth_detected_chunks = [smooth_detected_chunks; ii];
    end
end
smooth_detected_chunks = sort(smooth_detected_chunks);

%Plot detections
detects_to_plot = zeros(size(smooth_engs));
detects_to_plot(smooth_detected_chunks) = 1;
figure;
plot(detects_to_plot);
xlabel('Chunk Number');
ylabel('Detection (bool)');
title('Smoothed Detected Chunks');

%Compute the velocity for each chunk where a target was detected
H_det_chunks = H_chunks(detected_chunks,:);
[M, I] = max(H_det_chunks, [], 2);
detected_vels = abs(v_mph(I))';
target_vels = zeros(size(engs));
target_vels(detected_chunks) = detected_vels;

%Plot target velocities
figure;
plot(target_vels);
xlabel('Chunk Number');
ylabel('Velocity (mph)');
title('Target Velocities');

%Try to smooth velocities
%smoothed_vels = smoothdata(target_vels, 'movmean', 3);
smoothed_vels = target_vels;
for ii = 2:length(smoothed_vels)-1
    if ((target_vels(ii) == 0) && (target_vels(ii-1) > 0) && (target_vels(ii+1) > 0))
        smoothed_vels(ii) = (target_vels(ii-1) + target_vels(ii+1)) / 2;
    end
end

%Plot smoothed velocities
figure;
plot(smoothed_vels);
xlabel('Chunk Number');
ylabel('Velocity (mph)');
title('Smoothed Target Velocities');

%Show the frequency plot for each chunk individually on after the other
% fh = figure;
% for ii = 1:size(H_chunks, 1)
%     figure(fh);
%     plot(v_mph, abs(H_chunks(ii,:)));
%     xlabel('Veloctiy (mph)');
%     ylabel('Magnitude (Count)');
%     title(['Frequency Domain, Chunk = ' num2str(ii)]);
%     xlim([0, 40]);
%     pause;
% end

