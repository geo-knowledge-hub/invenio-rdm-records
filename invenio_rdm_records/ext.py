# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2022 CERN.
# Copyright (C) 2019-2021 Northwestern University.
# Copyright (C) 2022 Universität Hamburg.
# Copyright (C) 2022-2023 GEO Secretariat.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""DataCite-based data model for Invenio."""

import warnings

from flask import flash, g, request, session
from flask_babelex import _
from flask_iiif import IIIF
from flask_principal import identity_loaded
from invenio_records_resources.resources.files import FileResource
from invenio_records_resources.services import FileService
from itsdangerous import SignatureExpired

from invenio_rdm_records.oaiserver.resources.config import OAIPMHServerResourceConfig
from invenio_rdm_records.oaiserver.resources.resources import OAIPMHServerResource
from invenio_rdm_records.oaiserver.services.config import OAIPMHServerServiceConfig
from invenio_rdm_records.oaiserver.services.services import OAIPMHServerService

from . import config
from .customizations import load_class
from .resources import (
    IIIFResource,
    IIIFResourceConfig,
    RDMDraftFilesResourceConfig,
    RDMParentRecordLinksResource,
    RDMParentRecordLinksResourceConfig,
    RDMRecordFilesResourceConfig,
    RDMRecordResource,
    RDMRecordResourceConfig,
)
from .secret_links import LinkNeed, SecretLink
from .services import (
    IIIFService,
    RDMFileDraftServiceConfig,
    RDMFileRecordServiceConfig,
    RDMRecordService,
    RDMRecordServiceConfig,
    SecretLinkService,
)
from .services.pids import PIDManager, PIDsService
from .services.review.service import ReviewService


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


from flask import Blueprint

blueprint = Blueprint(
    "invenio_rdm_records",
    __name__,
    template_folder="templates",
    static_folder="static",
)


class InvenioRDMRecords(object):
    """Invenio-RDM-Records extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        self.init_services(app)
        self.init_resource(app)
        self.init_community_actions(app)
        app.before_request(verify_token)
        app.extensions["invenio-rdm-records"] = self
        app.register_blueprint(blueprint)
        # Load flask IIIF
        IIIF(app)

    def init_config(self, app):
        """Initialize configuration."""
        supported_configurations = [
            "FILES_REST_PERMISSION_FACTORY",
            "RECORDS_REFRESOLVER_CLS",
            "RECORDS_REFRESOLVER_STORE",
            "RECORDS_UI_ENDPOINTS",
            "THEME_SITEURL",
        ]

        for k in dir(config):
            if (
                k in supported_configurations
                or k.startswith("RDM_")
                or k.startswith("DATACITE_")
            ):
                app.config.setdefault(k, getattr(config, k))

        # set default communities namespaces to the global RDM_NAMESPACES
        if not app.config.get("COMMUNITIES_NAMESPACES"):
            app.config["COMMUNITIES_NAMESPACES"] = app.config["RDM_NAMESPACES"]

        # Deprecations
        # Remove when v6.0 LTS is no longer supported.
        deprecated = [
            ("RDM_RECORDS_DOI_DATACITE_ENABLED", "DATACITE_ENABLED"),
            ("RDM_RECORDS_DOI_DATACITE_USERNAME", "DATACITE_USERNAME"),
            ("RDM_RECORDS_DOI_DATACITE_PASSWORD", "DATACITE_PASSWORD"),
            ("RDM_RECORDS_DOI_DATACITE_PREFIX", "DATACITE_PREFIX"),
            ("RDM_RECORDS_DOI_DATACITE_TEST_MODE", "DATACITE_TEST_MODE"),
            ("RDM_RECORDS_DOI_DATACITE_FORMAT", "DATACITE_FORMAT"),
        ]
        for old, new in deprecated:
            if new not in app.config:
                if old in app.config:
                    app.config[new] = app.config[old]
                    warnings.warn(
                        f"{old} has been replaced with {new}. "
                        "Please update your config.",
                        DeprecationWarning,
                    )
            else:
                if old in app.config:
                    warnings.warn(
                        f"{old} is deprecated. Please remove it from your "
                        "config as {new} is already set.",
                        DeprecationWarning,
                    )

        self.fix_datacite_configs(app)

    #
    # Services generators
    #
    def service_configs(self, app):
        """Customized service configs."""

        class ClassContainer:
            record = load_class(
                "RDM_RECORD_SERVICE_CFG",
                app,
                default=RDMRecordServiceConfig,
                import_string=True,
                build=True,
            )

            file = load_class(
                "RDM_FILE_SERVICE_CFG",
                app,
                default=RDMFileRecordServiceConfig,
                import_string=True,
                build=True,
            )

            file_draft = load_class(
                "RDM_FILE_DRAFT_SERVICE_CFG",
                app,
                default=RDMFileDraftServiceConfig,
                import_string=True,
                build=True,
            )

            oaipmh = load_class(
                "RDM_OAIPMH_SERVICE_CFG",
                app,
                default=OAIPMHServerServiceConfig,
                import_string=True,
            )

        return ClassContainer

    def service_classes(self, app):
        """Service classes generator."""

        class ClassContainer:
            record = load_class(
                "RDM_RECORD_SERVICE", app, default=RDMRecordService, import_string=True
            )

            iiif = load_class(
                "RDM_IIIF_SERVICE", app, default=IIIFService, import_string=True
            )

            oiapmh = load_class(
                "RDM_OIAPMH_SERVICE",
                app,
                default=OAIPMHServerService,
                import_string=True,
            )

            file = load_class(
                "RDM_FILE_SERVICE", app, default=FileService, import_string=True
            )

            secret_link = load_class(
                "RDM_SECRET_LINK_SERVICE",
                app,
                default=SecretLinkService,
                import_string=True,
            )

            pid = load_class(
                "RDM_PID_SERVICE", app, default=PIDsService, import_string=True
            )

            review = load_class(
                "RDM_REVIEW_SERVICE", app, default=ReviewService, import_string=True
            )

        return ClassContainer

    #
    # Resources generators
    #
    def resource_configs(self, app):
        """Customized resources configs."""

        class ClassContainer:
            record = load_class(
                "RDM_RECORD_RESOURCE_CFG",
                app,
                default=RDMRecordResourceConfig,
                import_string=True,
                build=True,
            )

            file = load_class(
                "RDM_FILE_RESOURCE_CFG",
                app,
                default=RDMRecordFilesResourceConfig,
                import_string=True,
                build=True,
            )

            file_draft = load_class(
                "RDM_FILE_DRAFT_RESOURCE_CFG",
                app,
                default=RDMDraftFilesResourceConfig,
                import_string=True,
                build=True,
            )

            parent_link = load_class(
                "RDM_PARENT_LINK_RESOURCE_CFG",
                app,
                default=RDMParentRecordLinksResourceConfig,
                import_string=True,
                build=True,
            )

            oiapmh = load_class(
                "RDM_OIAPMH_RESOURCE_CFG",
                app,
                default=OAIPMHServerResourceConfig,
                import_string=True,
                build=True,
            )

            iiif = load_class(
                "RDM_IIIF_RESOURCE_CFG",
                app,
                default=IIIFResourceConfig,
                import_string=True,
                build=True,
            )

        return ClassContainer

    def resource_classes(self, app):
        """Resource classes generator."""

        class ClassContainer:
            record = load_class(
                "RDM_RECORD_RESOURCE",
                app,
                default=RDMRecordResource,
                import_string=True,
            )

            file = load_class(
                "RDM_FILE_RESOURCE",
                app,
                default=FileResource,
                import_string=True,
            )

            parent_link = load_class(
                "RDM_PARENT_RECORD_RESOURCE",
                app,
                default=RDMParentRecordLinksResource,
                import_string=True,
            )

            oiapmh = load_class(
                "RDM_OAIPMH_RESOURCE",
                app,
                default=OAIPMHServerResource,
                import_string=True,
            )

            iiif = load_class(
                "RDM_IIIF_RESOURCE", app, default=IIIFResource, import_string=True
            )

        return ClassContainer

    def init_services(self, app):
        """Initialize services."""
        service_configs = self.service_configs(app)
        service_classes = self.service_classes(app)

        # Services
        self.records_service = service_classes.record(
            service_configs.record,
            files_service=service_classes.file(service_configs.file),
            draft_files_service=service_classes.file(service_configs.file_draft),
            secret_links_service=service_classes.secret_link(service_configs.record),
            pids_service=service_classes.pid(service_configs.record, PIDManager),
            review_service=service_classes.review(service_configs.record),
        )

        self.iiif_service = service_classes.iiif(
            records_service=self.records_service, config=None
        )

        self.oaipmh_server_service = service_classes.oiapmh(
            config=service_configs.oaipmh,
        )

    def init_resource(self, app):
        """Initialize vocabulary resources."""
        resource_configs = self.resource_configs(app)
        resource_classes = self.resource_classes(app)

        self.records_resource = resource_classes.record(
            resource_configs.record,
            self.records_service,
        )

        # Record files resource
        self.record_files_resource = resource_classes.file(
            service=self.records_service.files, config=resource_configs.file
        )

        # Draft files resource
        self.draft_files_resource = resource_classes.file(
            service=self.records_service.draft_files, config=resource_configs.file_draft
        )

        # Parent Records
        self.parent_record_links_resource = resource_classes.parent_link(
            service=self.records_service, config=resource_configs.parent_link
        )

        # OAI-PMH
        self.oaipmh_server_resource = resource_classes.oiapmh(
            service=self.oaipmh_server_service,
            config=resource_configs.oiapmh,
        )

        # IIIF
        self.iiif_resource = resource_classes.iiif(
            service=self.iiif_service,
            config=resource_configs.iiif,
        )

    def fix_datacite_configs(self, app):
        """Make sure that the DataCite config items are strings."""
        datacite_config_items = [
            "DATACITE_USERNAME",
            "DATACITE_PASSWORD",
            "DATACITE_FORMAT",
            "DATACITE_PREFIX",
        ]
        for config_item in datacite_config_items:
            if config_item in app.config:
                app.config[config_item] = str(app.config[config_item])

    #
    # Extra customization properties
    #
    def init_community_actions(self, app):
        """Import and define the community actions in the RDM Extension."""

        class ClassContainer:
            create = load_class(
                "RDM_COMMUNITY_ACTION_CREATE",
                app,
                default=None,
                import_string=True,
            )

            submit = load_class(
                "RDM_COMMUNITY_ACTION_SUBMIT",
                app,
                default=None,
                import_string=True,
            )

            delete = load_class(
                "RDM_COMMUNITY_ACTION_DELETE",
                app,
                default=None,
                import_string=True,
            )

            accept = load_class(
                "RDM_COMMUNITY_ACTION_ACCEPT",
                app,
                default=None,
                import_string=True,
            )

            cancel = load_class(
                "RDM_COMMUNITY_ACTION_CANCEL",
                app,
                default=None,
                import_string=True,
            )

            decline = load_class(
                "RDM_COMMUNITY_ACTION_DECLINE",
                app,
                default=None,
                import_string=True,
            )

            expire = load_class(
                "RDM_COMMUNITY_ACTION_EXPIRE",
                app,
                default=None,
                import_string=True,
            )

        self.community_actions = ClassContainer
