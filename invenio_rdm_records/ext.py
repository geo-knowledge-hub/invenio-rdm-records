# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2021 CERN.
# Copyright (C) 2019-2021 Northwestern University.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""DataCite-based data model for Invenio."""

import warnings

from flask import flash, g, request, session
from flask_babelex import _
from flask_principal import identity_loaded
from invenio_records_resources.resources.files import FileResource
from invenio_records_resources.services import FileService
from invenio_vocabularies.contrib.affiliations import AffiliationsResource, \
    AffiliationsResourceConfig, AffiliationsService, \
    AffiliationsServiceConfig
from invenio_vocabularies.contrib.names import NamesResource, \
    NamesResourceConfig, NamesService, NamesServiceConfig
from invenio_vocabularies.contrib.subjects import SubjectsResource, \
    SubjectsResourceConfig, SubjectsService, SubjectsServiceConfig
from itsdangerous import SignatureExpired

from . import config
from .resources import RDMDraftFilesResourceConfig, \
    RDMParentRecordLinksResource, RDMParentRecordLinksResourceConfig, \
    RDMRecordFilesResourceConfig, RDMRecordResource, RDMRecordResourceConfig
from .secret_links import LinkNeed, SecretLink
from .services import RDMFileDraftServiceConfig, RDMFileRecordServiceConfig, \
    RDMRecordService, RDMRecordServiceConfig, SecretLinkService
from .services.pids import PIDManager, PIDsService
from .services.review.service import ReviewService
from .services.schemas.metadata_extensions import MetadataExtensions

from .customizations import load_config_class


def verify_token():
    """Verify the token and store it in the session if it's valid."""
    token = request.args.get("token", None)
    if token:
        try:
            data = SecretLink.load_token(token)
            if data:
                session["rdm-records-token"] = data

                # the identity is loaded before this handler is executed
                # so if we want the initial request to be authorized,
                # we need to add the LinkNeed here
                if hasattr(g, "identity"):
                    g.identity.provides.add(LinkNeed(data["id"]))

        except SignatureExpired:
            session.pop("rdm-records-token", None)
            flash(_("Your shared link has expired."))


@identity_loaded.connect
def on_identity_loaded(sender, identity):
    """Add the secret link token need to the freshly loaded Identity."""
    token_data = session.get("rdm-records-token")
    if token_data:
        identity.provides.add(LinkNeed(token_data["id"]))


class InvenioRDMRecords(object):
    """Invenio-RDM-Records extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        self.metadata_extensions = MetadataExtensions(
            app.config['RDM_RECORDS_METADATA_NAMESPACES'],
            app.config['RDM_RECORDS_METADATA_EXTENSIONS']
        )
        self.init_services(app)
        self.init_resource(app)
        app.before_request(verify_token)
        app.extensions['invenio-rdm-records'] = self

    def init_config(self, app):
        """Initialize configuration."""
        supported_configurations = [
            'FILES_REST_PERMISSION_FACTORY',
            'RECORDS_REFRESOLVER_CLS',
            'RECORDS_REFRESOLVER_STORE',
            'RECORDS_UI_ENDPOINTS',
            'THEME_SITEURL',
        ]

        for k in dir(config):
            if k in supported_configurations or k.startswith('RDM_') \
                or k.startswith('DATACITE_'):
                app.config.setdefault(k, getattr(config, k))

        # Deprecations
        # Remove when v6.0 LTS is no longer supported.
        deprecated = [
            ('RDM_RECORDS_DOI_DATACITE_ENABLED', 'DATACITE_ENABLED'),
            ('RDM_RECORDS_DOI_DATACITE_USERNAME', 'DATACITE_USERNAME'),
            ('RDM_RECORDS_DOI_DATACITE_PASSWORD', 'DATACITE_PASSWORD'),
            ('RDM_RECORDS_DOI_DATACITE_PREFIX', 'DATACITE_PREFIX'),
            ('RDM_RECORDS_DOI_DATACITE_TEST_MODE', 'DATACITE_TEST_MODE'),
            ('RDM_RECORDS_DOI_DATACITE_FORMAT', 'DATACITE_FORMAT'),
        ]
        for old, new in deprecated:
            if new not in app.config:
                if old in app.config:
                    app.config[new] = app.config[old]
                    warnings.warn(
                        f"{old} has been replaced with {new}. "
                        "Please update your config.",
                        DeprecationWarning
                    )
            else:
                if old in app.config:
                    warnings.warn(
                        f"{old} is deprecated. Please remove it from your "
                        "config as {new} is already set.",
                        DeprecationWarning
                    )

        self.fix_datacite_configs(app)

    def service_configs(self, app):
        """Customized service configs."""

        class ServiceConfigs:
            record = load_config_class(
                "RDM_RECORD_SERVICE_CFG",
                app,
                default=RDMRecordServiceConfig,
                import_string=True,
                build=True
            )

            file = load_config_class(
                "RDM_FILE_SERVICE_CFG",
                app,
                default=RDMFileRecordServiceConfig,
                import_string=True,
                build=True
            )

            file_draft = load_config_class(
                "RDM_FILE_DRAFT_SERVICE_CFG",
                app,
                default=RDMFileDraftServiceConfig,
                import_string=True,
                build=True
            )

            affiliations = AffiliationsServiceConfig
            names = NamesServiceConfig
            subjects = SubjectsServiceConfig

        return ServiceConfigs

    def resource_configs(self, app):
        """Customized resources configs."""

        class ResourceConfigs:
            record = load_config_class(
                "RDM_RECORD_RESOURCE_CFG",
                app,
                default=RDMRecordResourceConfig,
                import_string=True
            )

            file = load_config_class(
                "RDM_FILE_RESOURCE_CFG",
                app,
                default=RDMRecordFilesResourceConfig,
                import_string=True,
            )

            file_draft = load_config_class(
                "RDM_FILE_DRAFT_RESOURCE_CFG",
                app,
                default=RDMDraftFilesResourceConfig,
                import_string=True,
            )

            parent_link = load_config_class(
                "RDM_PARENT_LINK_RESOURCE_CFG",
                app,
                default=RDMParentRecordLinksResourceConfig,
                import_string=True,
            )

            affiliations = load_config_class(
                "RDM_AFFILIATIONS_RESOURCE_CFG",
                app,
                default=AffiliationsResourceConfig,
                import_string=True,
            )

            names = load_config_class(
                "RDM_NAMES_RESOURCE_CFG",
                app,
                default=NamesResourceConfig,
                import_string=True,
            )

            subjects = load_config_class(
                "RDM_SUBJECTS_RESOURCE_CFG",
                app,
                default=SubjectsResourceConfig,
                import_string=True,
            )

        return ResourceConfigs

    def init_services(self, app):
        """Initialize vocabulary resources."""
        service_configs = self.service_configs(app)

        # Services
        self.records_service = RDMRecordService(
            service_configs.record,
            files_service=FileService(service_configs.file),
            draft_files_service=FileService(service_configs.file_draft),
            secret_links_service=SecretLinkService(service_configs.record),
            pids_service=PIDsService(service_configs.record, PIDManager),
            review_service=ReviewService(service_configs.record),
        )
        self.affiliations_service = AffiliationsService(
            config=service_configs.affiliations,
        )
        self.names_service = NamesService(
            config=service_configs.names
        )
        self.subjects_service = SubjectsService(
            config=service_configs.subjects
        )

    def init_resource(self, app):
        """Initialize vocabulary resources."""
        resource_configs = self.resource_configs(app)

        self.records_resource = RDMRecordResource(
            resource_configs.record,
            self.records_service,
        )

        # Record files resource
        self.record_files_resource = FileResource(
            service=self.records_service.files,
            config=resource_configs.file
        )

        # Draft files resource
        self.draft_files_resource = FileResource(
            service=self.records_service.draft_files,
            config=resource_configs.file_draft
        )

        # Parent Records
        self.parent_record_links_resource = RDMParentRecordLinksResource(
            service=self.records_service,
            config=resource_configs.parent_link
        )

        # Vocabularies
        self.affiliations_resource = AffiliationsResource(
            service=self.affiliations_service,
            config=resource_configs.affiliations,
        )
        self.names_resource = NamesResource(
            service=self.names_service,
            config=resource_configs.names,
        )
        self.subjects_resource = SubjectsResource(
            service=self.subjects_service,
            config=resource_configs.subjects,
        )

    def fix_datacite_configs(self, app):
        """Make sure that the DataCite config items are strings."""
        datacite_config_items = [
            'DATACITE_USERNAME',
            'DATACITE_PASSWORD',
            'DATACITE_FORMAT',
            'DATACITE_PREFIX',
        ]
        for config_item in datacite_config_items:
            if config_item in app.config:
                app.config[config_item] = str(app.config[config_item])
