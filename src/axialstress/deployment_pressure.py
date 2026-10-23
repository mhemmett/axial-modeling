"""Fit reservoir pressure from deployment-relative bottom-pressure records.

Each deployment has its own unknown vertical datum. Differencing observations
within a deployment removes that datum before pressure inversion.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class DepthObservation:
    """Record one observed depth in meters at an inversion-grid index."""

    deployment: str
    time_index: int
    depth_m: float


@dataclass(frozen=True)
class RelativePressureFit:
    """Store a datum-free Center fit relative to zero pressure at grid start."""

    pressure_mpa: FloatArray
    predicted_relative_uplift_m: FloatArray
    observed_relative_uplift_m: FloatArray
    observation_deployments: tuple[str, ...]
    observation_time_indices: NDArray[np.int64]
    rmse_m: float
    design_rank: int


def fit_deployment_relative_pressure(
    pressure_to_uplift_m_per_mpa: FloatArray,
    observations: list[DepthObservation],
    *,
    curvature_weight: float = 1.0,
    deployment_response: dict[str, FloatArray] | None = None,
) -> RelativePressureFit:
    """Fit pressure to within-deployment depth changes in meters.

    Parameters
    ----------
    pressure_to_uplift_m_per_mpa : numpy.ndarray
        Square PyLith response operator. Row and column zero represent the
        baseline, whose pressure and uplift must both be zero.
    observations : list[DepthObservation]
        Source depths at exact model-grid times. Each deployment needs at
        least two samples. Depth increase means subsidence.
    curvature_weight : float
        Dimensionless coefficient on squared pressure second differences.
    deployment_response : dict[str, numpy.ndarray], optional
        Site-specific operators for deployments with distinct coordinates.
        The common operator applies to any deployment not in this mapping.

    Returns
    -------
    RelativePressureFit
        Pressure, datum-free fit, and observation-level residual diagnostics.

    Notes
    -----
    The first depth in each deployment is an independent reference. No
    cross-deployment offset or pressure is inferred directly from observations
    inside a gap. Curvature regularization supplies a conditional path there.
    The initial zero-pressure state is an explicit model assumption.
    """
    response = np.asarray(pressure_to_uplift_m_per_mpa, dtype=float)
    if (
        response.ndim != 2
        or response.shape[0] != response.shape[1]
        or response.shape[0] < 3
        or not np.all(np.isfinite(response))
        or not np.allclose(response[0], 0.0)
        or not np.allclose(response[:, 0], 0.0)
    ):
        raise ValueError("response must be a finite square baseline-zero operator")
    if not np.isfinite(curvature_weight) or curvature_weight < 0.0:
        raise ValueError("curvature weight must be finite and nonnegative")
    if not observations:
        raise ValueError("at least one deployment is required")
    site_responses = deployment_response or {}
    for deployment, site_response in site_responses.items():
        if (
            not deployment
            or np.asarray(site_response).shape != response.shape
            or not np.all(np.isfinite(site_response))
            or not np.allclose(site_response[0], 0.0)
            or not np.allclose(site_response[:, 0], 0.0)
        ):
            raise ValueError("deployment response must match the baseline-zero operator")
    grouped: dict[str, list[DepthObservation]] = {}
    for item in observations:
        if (
            not item.deployment
            or not 0 <= item.time_index < len(response)
            or not np.isfinite(item.depth_m)
        ):
            raise ValueError("observation has invalid deployment, index, or depth")
        grouped.setdefault(item.deployment, []).append(item)

    design_rows = []
    observed_changes = []
    deployment_labels = []
    indices = []
    for deployment, records in sorted(grouped.items()):
        site_response = site_responses.get(deployment, response)
        records.sort(key=lambda item: item.time_index)
        if len(records) < 2 or len({item.time_index for item in records}) != len(records):
            raise ValueError(f"deployment {deployment} needs distinct grid samples")
        reference = records[0]
        for item in records[1:]:
            design_rows.append(
                site_response[item.time_index, 1:] - site_response[reference.time_index, 1:]
            )
            observed_changes.append(reference.depth_m - item.depth_m)
            deployment_labels.append(deployment)
            indices.append(item.time_index)
    design = np.asarray(design_rows, dtype=float)
    observed = np.asarray(observed_changes, dtype=float)
    compliance = float(np.median(np.diag(response)[1:]))
    if compliance <= 0.0:
        raise ValueError("response must have positive pressure compliance")
    uplift_scale_m = max(float(np.std(observed)), 1.0e-6)
    pressure_scale_mpa = uplift_scale_m / compliance
    curvature = np.diff(np.eye(len(response)), n=2, axis=0)[:, 1:]
    augmented = np.vstack(
        (
            design * pressure_scale_mpa / uplift_scale_m,
            np.sqrt(curvature_weight) * curvature,
        )
    )
    target = np.concatenate((observed / uplift_scale_m, np.zeros(len(curvature))))
    solution, _, rank, _ = np.linalg.lstsq(augmented, target, rcond=None)
    if rank != len(response) - 1:
        raise ValueError("pressure history is not identified under this regularization")
    pressure = np.concatenate(([0.0], solution * pressure_scale_mpa))
    predicted = design @ pressure[1:]
    return RelativePressureFit(
        pressure_mpa=pressure,
        predicted_relative_uplift_m=predicted,
        observed_relative_uplift_m=observed,
        observation_deployments=tuple(deployment_labels),
        observation_time_indices=np.asarray(indices, dtype=np.int64),
        rmse_m=float(np.sqrt(np.mean((predicted - observed) ** 2))),
        design_rank=int(np.linalg.matrix_rank(design)),
    )
