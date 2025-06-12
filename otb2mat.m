function vars = otb2mat(path, filename, savepath, savefilename, savefile)
% OTB2MAT Transform .otb+ file to .mat file, in the .otb+ format.
%   Untar .otb+ files, load signal from .sig file and parameters from the 
%   corresponding .xml file (both with the same name), and convert digital 
%   units to microvolts.
%
%   :param path: char, path to folder in which file is stored.
%   :param filename: char, name of .otb+ file.
%   :param savepath: char, path to folder in which file will be stored (if
%   empty, same as path).
%   :param savefilename: char, name of resulting .mat file (if empty, save 
%   as filename).
%   :param savefile: boolean, = 1 save .mat, = 0 return vars without saving.
%
%   :return: structure, with variables corresponding to .otb+ format.
%
%   :usage: otb2mat('C:\Users\myuser\mydir', 'myfile.otb+')
%   :version: MATLAB R2025a
%
% Note: analog output signals are updated at the same sample frequency used
% for the input signals but with a delay of 40 samples (78.12, 19.53, 7.81,
% or 3.9 ms for 512, 2048, 5120, or 10240 Hz, respectively.
%
% Note: actual sampling frequency differs slightly from metadata.
%
% Created by Blanca Delgado Bonet (bdelgado@unizar.es)
% July 2025, last edit: 2025-06-10

UnitFactor = 10^6;  % volts to microvolts
UnitLabel = char(hex2dec('03BC'));

if isempty(savepath), savepath = path; end
if isempty(savefilename), savefilename = replace(filename, '.otb+', '.mat'); end

try 
    %% Untar .otb file in temporary folder
    folderpath = pwd;
    foldername = 'temp-' + string(datetime('now', 'Format', 'yyMMddHHmmss'));
    mkdir(foldername)
    cd(foldername)
    untar(fullfile(path, filename))
    cd ..

    %% Find .sig
    signal = dir(fullfile(foldername, "*.sig"));  % filename
    time = replace(signal.name, '.sig', '');  % identifier

    %% Load parameters
    param = readstruct(fullfile(signal.folder, time + ".xml"), 'AttributeSuffix', '');
    fs = param.SampleFrequency;
    nch = param.DeviceTotalChannels;

    info = cell(nch, 1);
    extra_vals = nan(nch, 3);  % Gain, HighPassFilter, LowPassFilter
    extra_info = strings(nch, 4);  % Channel ID, Prefix + Description, Muscle, Side 
    ii = 1;
    for i_adapter = 1:length(param.Channels.Adapter)
        gain = param.Channels.Adapter(i_adapter).Gain;
        hpfilter = param.Channels.Adapter(i_adapter).HighPassFilter;
        lpfilter = param.Channels.Adapter(i_adapter).LowPassFilter;

        for i_ch = 1:length(param.Channels.Adapter(i_adapter).Channel)
            channel = param.Channels.Adapter(i_adapter).Channel(i_ch);

            info{ii} = sprintf("%s - %s %s (%i)[%sV]", channel.Muscle, channel.Prefix, channel.ID, channel.Index + 1, UnitLabel);
            extra_vals(ii, :) = [gain; hpfilter; lpfilter];
            extra_info(ii, :) = [channel.ID; channel.Prefix + " " + channel.Description; channel.Muscle; channel.Side];
            ii = ii + 1;
        end
    end


    %% Load signal
    f = fopen(fullfile(signal.folder, signal.name));
    if f == -1
        error('Unable to load signal.')
    end
    x = fread(f,[nch,inf],'short')';
    fclose(f);

    % Convert digital units into voltage units:
    Resolution = param.ad_bits;  % bits
    InputRange = 5;  % V
    Gain = extra_vals(:, 1);
    GainFactor = InputRange ./ 2^Resolution ./ Gain;  % digital units to volts
    
    x = x .* GainFactor' .* UnitFactor;

    %% Save variables
    vars.Data = x;
    vars.Description = info;
    vars.Details = extra_info;
    vars.OTBFile = filename;
    vars.SamplingFrequency = fs;

    vars.SamplingFrequencyReal = 'undefined';
    if fs == 2048
        fs = 2042.483;
        vars.SamplingFrequencyReal = fs;
    elseif fs == 10240
        fs = 10212.4;
        vars.SamplingFrequencyReal = fs;
    end

    vars.Time = (0:size(x, 1)-1)'./fs;

    if savefile
        save(fullfile(savepath, savefilename), '-struct', 'vars', '-v7.3')
    end

    % Remove temporary directory:
    rmdir(fullfile(folderpath, foldername), 's')

catch ME
    fclose all;
    rmdir(fullfile(folderpath, foldername), 's')
    error('%s\nError using %s (line %i)',ME.message, ME.stack.name, ME.stack.line);     
end
end