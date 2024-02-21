# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 GEO Secretariat.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Customization functionality."""

from flask import current_app
from invenio_base.utils import load_or_import_from_config


class OverridableField:
    """Overridable field for simple class-level customization."""

    #
    # Auxiliary methods
    #
    def _get_configuration(self, configuration_source):
        """Read data description configurations."""
        # reading configuration from the source
        configuration_name = getattr(configuration_source, "config_variable")
        configuration_obj = current_app.config.get(configuration_name, {})

        return configuration_obj

    #
    # Data Descriptor methods.
    #
    def __init__(self, key, default_value):
        """Initializer."""
        self._key = key
        self._default_value = default_value

    def __get__(self, instance, owner):
        """Get field value."""
        field_configuration = self._get_configuration(instance or owner)

        return field_configuration.get(self._key) or self._default_value

    def __set__(self, instance, value):
        """Set field value."""
        raise AttributeError()


def load_class(config_key, app_ctx, default=None, import_string=False, build=False):
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
