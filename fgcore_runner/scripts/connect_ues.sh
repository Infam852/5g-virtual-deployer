#!/bin/bash

set -ux

N_UES="${1:-"10"}"  # number of ues start in one iteration
N_ITERATIONS="${2:-"10"}"
LOG_FILE=${3:-"/home/ops/logs/connect-ue-$(date +"%H-%M-%S-%6N").log"}
TIMEOUT=${4:-"5"}   # stop ues after timeout

SCRIPT_PATH="/home/ops/scripts/bootstrap_ue.sh"
UE_CONFIG_PATH="/home/ops/nf_configs/ue-template.yml"
UE_NUM="1"

mkdir configs $(dirname ${LOG_FILE})

for i in $(seq 1 $N_ITERATIONS)
do
    IMSI="imsi-00101$(printf %010d ${UE_NUM})"  # pad to 10 0s
    UE_CONFIG="configs/ue-config-${UE_NUM}.yml"
    sed "s/|IMSI|/${IMSI}/" ${UE_CONFIG_PATH} > ${UE_CONFIG}

    echo "$(date +%T%3N) - iteration $i - start ${N_UES} ues: first idx ${UE_NUM}"
    timeout ${TIMEOUT} sudo ${SCRIPT_PATH} ${UE_NUM} ${N_UES} $(pwd) ${UE_CONFIG} &>> ${LOG_FILE} &
    UE_NUM=$(($UE_NUM + $N_UES))
    sleep 1
done

# grep for interface if needed
# cat logs/9487f9799671a1c7.log | grep -o -P '(?<=interface\[).*(?=,)'
