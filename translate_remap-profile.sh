
export NDSL_LOGLEVEL="Debug"

# py-spy record -f speedscope -o d_sw-orch-dace-cpu-ijk-warm.json -- \
# python3 -m scalene run --profile-all --stacks --- -m pytest -vs \
python -m pytest -vs \
    --data_path=test_data/8.1.3/c12_6ranks_standard/dycore \
    --backend=st:dace:cpu:KIJ \
    --which_modules=CS_Profile_2d \
    --which_rank=0 \
    --threshold_overrides_file=./tests/savepoint/translate/overrides/standard.yaml \
    ./tests/savepoint/

    # --backend=st:numpy:cpu:IJK \ # numpy
    # --backend=st:dace:cpu:IJK \  # dace stencil
    # --backend=orch:dace:cpu:KIJ \ # previously "dace:cpu"        <- okay
    # --backend=orch:dace:cpu:KJI \ # previously "dace:cpu_KJI"    <- ValueError: could not broadcast input array from shape (80,) into shape (79,); line: `pfull.data[:] = pfull.np.asarrray(inputs.pop("pfull"))`
    # --backend=orch:dace:cpu:IJK \ # previously "dace:cpu_kfirst" <- invalid SDFG

# ['delp', 'w', 'ps', 'dp1']
