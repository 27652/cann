#!/usr/bin/env python3
"""Read-only, toolkit-specific source audit; no network or device execution.

The checks intentionally fail if relevant header text changes. They establish
source/API facts, not measured stage costs or universal hardware impossibility.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def require(text, snippet):
    if snippet not in text:
        raise ValueError('Toolkit implementation changed; re-audit: ' + snippet)


def audit(toolkit):
    asc = toolkit / 'x86_64-linux/asc'
    paths = {
        'utils': asc / 'impl/adv_api/detail/matmul/utils/matmul_utils.h',
        'chip': asc / 'impl/adv_api/detail/matmul/feature_trait/matmul_chip_cap.h',
        'trait': asc / 'impl/adv_api/detail/matmul/feature_trait/matmul_feature_trait.h',
        'client': asc / 'include/adv_api/matmul/matmul_client.h',
        'server': asc / 'impl/adv_api/detail/matmul/kfc/matmul_server_impl_c220.h',
        'fixpipe': asc / 'impl/basic_api/dav_c220/kernel_operator_fixpipe_impl.h',
        'kernel': ROOT / 'kernel.asc',
        'evidence': ROOT / 'evidence/formal/dual-aiv-fixed-6ad33b78/evidence.json',
        'historical_comparison': ROOT / 'optimization/TBEST_ANALYSIS_20261017.md',
    }
    data = {name: path.read_text() for name, path in paths.items()}
    require(data['utils'], '#if defined(__NPU_ARCH__) && __NPU_ARCH__ == 3510')
    require(data['utils'], '#else\n#define USE_WORKSPACE\n#endif')
    require(data['chip'], '__NPU_ARCH__ == 2201\n        return CHIP_TYPE_220;')
    fields = re.findall(r'(?:bool|FixpipeParamsType)\s+(\w+)\s*;',
                        data['chip'].split('struct Feature {', 1)[1].split('};', 1)[0])
    row = re.search(r'/\*220\*/\s*\{([^}]+)\}', data['chip'])
    values = [v.strip() for v in row.group(1).split(',')]
    if len(fields) != len(values):
        raise ValueError('Capability table layout changed')
    features = dict(zip(fields, values))
    assert features['ifSupportL0CToUB'] == 'false'
    require(data['trait'], 'return MatmulChipCap::GetFeatures().ifSupportL0CToUB;')
    require(data['client'], 'auto gmDataAddr = client->AllocUB(size, kfcMsg_.ubAddr);')
    require(data['client'], 'kfcMsg_.body.cAddr = GetGlobalAddr<typename C_TYPE::T, false>(c);')
    require(data['client'], 'CopyToUB(c, (__gm__ DstT*)gmDataAddr, c.GetSize());')
    require(data['client'], 'CopyToUB(co2Local, gm.GetPhyAddr(), co2Local.GetSize());')
    require(data['client'], 'CopyToUB<DstT, uint8_t, false>(c, cacheWorkspaceAddr + cOffset_, c.GetSize());')
    require(data['server'], 'if constexpr (PhyPosIsL1(C_TYPE::pos)) {')
    require(data['server'], 'cGlobal.SetGlobalBuffer(reinterpret_cast<__gm__ DstT*>(msg->body.cAddr), size);')
    require(data['fixpipe'], '// L0C->L1')
    require(data['fixpipe'], 'FixpipeL0C2L1Impl((__cbuf__ PrimT<T>*)dst.GetPhyAddr(),')
    evidence = json.loads(data['evidence'])
    assert evidence['submission_id'] == '6ad33b78193e507d8ea310c4'
    assert evidence['score_evidence']['submission_id'] == evidence['submission_id']
    assert evidence['score_evidence']['value'] == '19.45'
    assert len(evidence['testcases']) == 15
    assert all(c['testcase_status'] == 'Pass' and c['precision_ratio'] == 1
               for c in evidence['testcases'])
    root_hash = hashlib.sha256(paths['kernel'].read_bytes()).hexdigest()
    assert root_hash == evidence['files']['kernel.asc'], 'Root changed; re-establish baseline'
    ratios = [
        {'point': i, 'testcase_id': c['testcase_id'],
         'time_us': c['time'], 'best_time_us': c['best_time'],
         'time_over_best': c['time'] / c['best_time']}
        for i, c in enumerate(evidence['testcases'], 1)
    ]
    return {
        'kind': 'source_api_audit_not_device_or_stage_measurement',
        'target': 'dav-2201',
        'features': features,
        'get_tensor_c_local_transport': 'internal GM staging then GM-to-UB copy',
        'direct_l0c_to_ub_supported_by_installed_matmul': False,
        'baseline_submission_id': evidence['submission_id'],
        'baseline_official_score': evidence['score_evidence']['value'],
        'baseline_kernel_sha256': root_hash,
        'baseline_times': ratios,
        'min_time_over_best': min(r['time_over_best'] for r in ratios),
        'max_time_over_best': max(r['time_over_best'] for r in ratios),
        'historical_comparison_submission_id': '6ad2cb6b193e507d8e02c24b',
        'inputs': {name: {'path': str(path),
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                   for name, path in paths.items()},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolkit', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.toolkit.resolve()), indent=2))
