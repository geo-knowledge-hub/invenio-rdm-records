# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 CERN.
# Copyright (C) 2019 Northwestern University.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Customization functionality."""

from invenio_base.utils import load_or_import_from_config


def load_config_class(
    config_key, app_ctx, default=None, import_string=False, build=False
):
    """Function to load services configuration.

    See:
        https://docs.python.org/3/howto/descriptor.html
    Note:
        This function is based on `invenio_rdm_records.services.customizations.FromConfig`.
    """
    res = None

    if import_string:
        res = load_or_import_from_config(app=app_ctx, key=config_key, default=default)
    else:
        res = app_ctx.config.get(config_key, default)

    if res and build:
        res = res.build(app_ctx)

    return res
