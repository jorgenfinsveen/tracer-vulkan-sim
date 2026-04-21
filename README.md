# Installation guide

This repository is forked from https://github.com/JRPan/crisp-artifact and slightly adjusted in order to run on the IDUN cluster computer at the Norwegian University of Science and Technology.

## Setup on host

### Cloning
```bash
mkdir -p "$HOME/projects" && cd "$HOME/projects"
git clone https://github.com/jorgenfinsveen/tracer-vulkan-sim.git crisp_framework
export CRISP_ROOT="$HOME/projects/crisp_framework"
export INSTALL_SETUP="$CRISP_ROOT/.install/setup"
```

### Creating necessary directories
```bash
mkdir -p "$HOME"/{opt,usr/local,.environments/python,traces/logs,traces/tracefiles}
```

### Installing a Python environment
```bash
# IMPORTANT: Check that you have python 3.10 or newer
python3 -m venv "$HOME/.environments/python/env"
cp -r "$IDUN_SETUP/pyenv" "$HOME"
chmod +x "$HOME/pyenv" && source "$HOME/pyenv"

pip install -r "$INSTALL_SETUP/requirements.txt"
```

### Installing CUDA
```bash
export CUDA_VERSION="11.7"
export CUDA_DEST="$HOME/usr/local/cuda/cuda-$CUDA_VERSION"
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/11.7.0/local_installers/cuda-repo-ubuntu2004-11-7-local_11.7.0-515.43.04-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2004-11-7-local_11.7.0-515.43.04-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2004-11-7-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda

mkdir -p "$HOME/usr/local/bin" "$HOME/usr/local/cuda"
cp -r "$CUDA_HOME" "$CUDA_DEST"
ln -s "$CUDA_DEST" "$HOME/usr/local/bin/cuda"
```

### Installing Embree3
```bash
export EMBREE_VERSION="3.13.5"
export EMBREE_INSTALL="$HOME/opt/embree3.tgz"
export EMBREE_VARS="$HOME/opt/embree-$EMBREE_VERSION.x86_64.linux/embree-vars.sh"
export EMBREE_URL="https://github.com/embree/embree/releases/download/v$EMBREE_VERSION/embree-$EMBREE_VERSION.x86_64.linux.tar.gz"

wget -O "$EMBREE_INSTALL" "$EMBREE_URL"
tar xzf "$EMBREE_INSTALL" && rm -f "$EMBREE_INSTALL"
source "$EMBREE_VARS"
```

### Installing VulkanSDK
```bash
export VULKAN_VERSION="1.3.296.0"
export VULKAN_DIR="$HOME/opt/vulkansdk"
export VULKAN_INSTALL="$VULKAN_DIR/vulkansdk.tar.xz"
export VULKAN_URL="https://sdk.lunarg.com/sdk/download/${VULKAN_VERSION}/linux/vulkansdk-linux-x86_64-${VULKAN_VERSION}.tar.xz?Human=true"

mkdir -p "$VULKAN_DIR" && cd "$VULKAN_DIR"
wget -O "$VULKAN_INSTALL" "$VULKAN_URL"
tar -xf "$VULKAN_INSTALL" && rm -f "$VULKAN_INSTALL"
ln -sfn "${VULKAN_VERSION}" current
```



## Building


### Building CRISP
```bash
cd "$HOME/projects/crisp_framework"
source build_env.sh

# This builds vulkan-sim and mesa-vulkan-sim
build_vulkan

# This builds accel-sim and gpgpu-sim
build_accelsim_hard
```


## Next steps

### Install Vulkan-Samples

```bash
cd "$HOME/projects"
git clone https://github.com/SaschaWillems/Vulkan.git Vulkan-Samples

# Follow instructions in README to build Vulkan-Sim from here
```

### Install Monado

```bash
cd "$HOME/projects"
git clone https://github.com/SaschaWillems/Vulkan.git Monado

# Follow instructions in README to build Monado from here
``` 

### Install Godot

```bash
cd "$HOME/projects"
git clone https://github.com/JRPan/godot.git Godot

# Follow instructions in README to build Godot from here
``` 


## Make traces

### Setup

```bash
mkdir -p "$HOME/traces/logs" "$HOME/traces/tracefiles"

export PROJECTS="$HOME/projects"
export CRISP_ROOT="$PROJECS/crisp_framework"
export VK_SAMPLES_ROOT="$PROJECTS/Vulkan-Samples"
export MONADO_ROOT="$PROJECTS/Monado"
export GODOT_ROOT="$PROJECTS/Godot"

ln -s "$CRISP_ROOT/setup_environment.sh" "$PROJECTS"

cp "$CRISP_ROOT/gpgpusim.config" "$VK_SAMPLES_ROOT"
cp "$CRISP_ROOT/config_turing_islip.icnt" "$VK_SAMPLES_ROOT"

cp "$CRISP_ROOT/gpgpusim.config" "$MONADO_ROOT"
cp "$CRISP_ROOT/config_turing_islip.icnt" "$MONADO_ROOT"

cp "$CRISP_ROOT/gpgpusim.config" "$GODOT_ROOT"
cp "$CRISP_ROOT/config_turing_islip.icnt" "$GODOT_ROOT"

```

### See available samples

```bash 
source "$HOME/projects/setup_environment.sh"

# For Vulkan-Samples
vksamples

# For Monado
monado

```

### Start tracing

```bash

source "$HOME/projects/setup_environment.sh"

# Set resolution
tracer_resolution [RESOLUTION] # Alternatives: 480p|720p|HD|QHD|4K-UHD

# For Vulkan-Samples
vksamples [SAMPLE_NAME]

# For Monado
monado [SAMPLE_NAME]

```

### Inspecting results

* Traces are stored in the root-folder of Vulkan-Samples/Monado
* While the tracer runs, the file will be named ```traces.traceg```.
* When the tracer is finished, the fill will be renamed to ```complete.trageg```.
* Logs from the tracer will be located at ```~/traces/logs```.

### Common error-causes

#### Make sure the following environment variables are set

* VK_ICD_FILENAMES: Should point to a file named ```intel_icd.x86_64.json```.
* PATH
* LD_LIBRARY_PATH
* CC_VERSION: Should be ```9.4.0```.
* CUDA_VERSION: Should be ```11.7```.
* CUDART_VERSION: Should be ```11070```.
* CUDA_HOME
* CUDA_INSTALL_PATH
* GPGPUSIM_CONFIG
* GPGPUSIM_ROOT
* ROOT
* VULKAN_SIM
* MESA_SIM
* MESA_ROOT
* TRACER_RESOLUTION_X: Must exist during runtime.
* TRACER_RESOLUTION_Y: Must exist during runtime.

#### Make sure that these commands don't fail

* ```nvcc```
* ```vulkaninfo``` 
* ```gcc```

#### Make sure that you're NOT using SSH

You need to operate the machine physically to make traces
