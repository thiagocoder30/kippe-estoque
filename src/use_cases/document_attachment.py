"""
Integração segura entre armazenamento físico de documentos
e sua evidência documental persistida.

O arquivo físico é publicado primeiro.

A persistência documental posterior é atômica no repository.
Se essa persistência falhar, o arquivo físico recém-criado é
removido como compensação.
"""

from __future__ import annotations


class DocumentAttachmentIntegrationError(RuntimeError):
    """
    Falha composta na integração documental.

    Utilizada quando a operação principal falha e a compensação
    física também não consegue restaurar o estado anterior.
    """


class AttachDocumentToAuditEventUseCase:
    """
    Coordena storage físico e persistência documental.

    Nenhuma lógica de estoque pertence a este caso de uso.
    """

    def __init__(
        self,
        *,
        repository,
        storage,
    ):
        self.repository = repository
        self.storage = storage

    def attach(
        self,
        *,
        event_id,
        content,
        original_filename,
        declared_mime_type,
        business_document_number="",
        supplier="",
        operator_id,
    ):
        normalized_operator_id = str(
            operator_id or ""
        ).strip()

        if not normalized_operator_id:
            raise ValueError(
                "operator_id é obrigatório."
            )

        try:
            normalized_event_id = int(
                event_id
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "event_id deve ser um inteiro positivo."
            ) from exc

        if normalized_event_id <= 0:
            raise ValueError(
                "event_id deve ser um inteiro positivo."
            )

        descriptor = self.storage.store(
            content=content,
            original_filename=original_filename,
            declared_mime_type=declared_mime_type,
        )

        relative_path = descriptor[
            "relative_path"
        ]

        try:
            attachment_id = (
                self.repository
                .create_and_link_document_attachment(
                    event_id=normalized_event_id,
                    attachment_id=descriptor[
                        "attachment_id"
                    ],
                    business_document_number=(
                        business_document_number
                    ),
                    supplier=supplier,
                    original_filename=descriptor[
                        "original_filename"
                    ],
                    stored_filename=descriptor[
                        "stored_filename"
                    ],
                    relative_path=relative_path,
                    mime_type=descriptor[
                        "mime_type"
                    ],
                    byte_size=descriptor[
                        "byte_size"
                    ],
                    sha256=descriptor[
                        "sha256"
                    ],
                    operator_id=normalized_operator_id,
                )
            )

        except Exception as persistence_error:
            try:
                self.storage.delete(
                    relative_path
                )

            except Exception as compensation_error:
                raise DocumentAttachmentIntegrationError(
                    "Falha na persistência documental e "
                    "falha na compensação do arquivo físico."
                ) from compensation_error

            raise persistence_error

        result = dict(
            descriptor
        )

        result[
            "attachment_id"
        ] = attachment_id

        return result
