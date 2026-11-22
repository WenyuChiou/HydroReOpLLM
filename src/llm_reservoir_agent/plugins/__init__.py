"""Namespace for optional adapters to pinned external policy implementations.

Installed plugin modules connect package contracts to explicitly selected
external policies; ``experiment`` includes their Python bytes in implementation
provenance. Native reservoir flow uses m3/s and storage uses m3, while each
adapter documents any external unit conversion. This namespace itself exports
no backend, reads no policy files, starts no simulation and sends no request.
Import a specific integration only when its optional dependencies are available.
"""
