#!/usr/bin/env bash
export PROJECTS_DIR="$HOME/projects"
export ROOT="$PROJECTS_DIR/crisp_framework"
export VULKAN_SIM="$ROOT/vulkan-sim"
export MESA_SIM="$ROOT/mesa-vulkan-sim"
export MESA_ROOT="$ROOT/mesa-vulkan-sim"
export ACCEL_SIM="$ROOT/accel-sim-framework"
export ACCELSIM_ROOT="$ACCEL_SIM"
export VK_ICD_FILENAMES="$MESA_SIM/lib/share/vulkan/icd.d/intel_icd.x86_64.json"
export CC_VERSION="9.4.0"
export VK_SAMPLES_DIR="$PROJECTS_DIR/Vulkan-Samples"
export MONADO_DIR="$PROJECTS_DIR/Monado"

# CUDA
export CUDA_VERSION="11.7"
export CUDART_VERSION="11070"
export CUDA_HOME="$HOME/usr/local/bin/cuda"
export CUDA_INSTALL_PATH="$HOME/usr/local/bin/cuda"

# Embree
export EMBREE_VERSION="3.13.5"
export EMBREE_ROOT="$HOME/opt/embree-$EMBREE_VERSION.x86_64.linux"
export EMBREE_DIR="$EMBREE_ROOT"
export embree_DIR="$EMBREE_ROOT/lib/cmake/embree-$EMBREE_VERSION"

# VulkanSDK
export VULKAN_VERSION="1.3.296.0"
export VULKAN_SDK="$HOME/opt/vulkansdk/current/x86_64"

# Paths
export PATH="$VULKAN_SDK/bin:$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$EMBREE_ROOT/lib:$CUDA_HOME/lib64:$VULKAN_SDK/lib:$LD_LIBRARY_PATH"

source "$ROOT/vulkan-sim/setup_environment"




export TRACE_DEBUG_LOGDIR="$HOME/traces/logs"
export VULKAN_SAMPLES_EXECUTABLE="$VK_SAMPLES_DIR/build/linux/app/bin/Release/x86_64/vulkan_samples"
export MONADO_EXECUTABLE_DIR="$MONADO_DIR/bin"

sample() {
	VULKAN_APP="$1"	$VULKAN_SAMPLES sample "$1" >> "$VK_SAMPLES_DIR/$2.log"
}


monado() {
	if (( $# == 0 )); then
		ls $MONADO_EXECUTABLE_DIR
	elif [[ "$1" == "list" ]]; then
		ls $MONADO_EXECUTABLE_DIR
	else
		MONTH_DIR=$(date +"%m_%d")
		DAY_STR=$(date +"%H_%M")
		mkdir -p "$TRACE_DEBUG_LOGDIR/$MONTH_DIR/monado"
		current_dir=$(pwd)
		cd "$MONADO_DIR"
		VULKAN_APP="$1" "$MONADO_EXECUTABLE_DIR/$1" >> "$TRACE_DEBUG_LOGDIR/$MONTH_DIR/monado/$DAY_STR.log"
		cd "$current_dir"
	fi
}

vksamples() {
	if (( $# == 0 )); then
		$VULKAN_SAMPLES_EXECUTABLE samples-oneline
	elif [[ "$1" == "list" ]]; then
		$VULKAN_SAMPLES_EXECUTABLE samples-oneline
	else
		MONTH_DIR=$(date +"%m_%d")
		DAY_STR=$(date +"%H_%M")
		mkdir -p "$TRACE_DEBUG_LOGDIR/$MONTH_DIR/vksamples"
		current_dir=$(pwd)
		cd "$VK_SAMPLES_DIR"
		VULKAN_APP="$1" "$VULKAN_SAMPLES_EXECUTABLE" sample "$1" >> "$TRACE_DEBUG_LOGDIR/$MONTH_DIR/vksamples/$DAY_STR.log"
		cd "$current_dir"
	fi

}
