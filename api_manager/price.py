from typing import Dict, List, Optional, Any
from .base import BaseAPI


class PriceAPI(BaseAPI):
    def __init__(self, http_client, logger, product_url: str):
        super().__init__(http_client, logger)
        self.product_url = product_url

    def _prepare_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalised = {k: v for k, v in payload.items() if v is not None}
        if "unitPrice" in normalised:
            normalised["unitPrice"] = float(normalised["unitPrice"])
        if "specialOfferPrice" in normalised and normalised["specialOfferPrice"] is not None:
            normalised["specialOfferPrice"] = float(normalised["specialOfferPrice"])
        elif "specialOfferPrice" in normalised:
            normalised.pop("specialOfferPrice", None)
        return normalised

    def update_product_prices(self, product_number: str, operations: List[Dict[str, Optional[Dict[str, Any]]]]) -> bool:
        url = f"{self.product_url}/{product_number}/prices"
        try:
            for operation in operations:
                delete_payload = operation.get("delete") if operation else None
                update_payload = operation.get("update") if operation else None
                create_payload = operation.get("create") if operation else None

                if delete_payload:
                    self.logger.warning(f"Preparing to delete prices for {product_number}: {delete_payload}")
                    if not delete_payload.get("unitPrice"):
                        self.logger.error(f"Invalid delete payload for {product_number}: {delete_payload}")
                        continue
                    prepared_delete = self._prepare_payload(delete_payload)
                    self.logger.debug(f"Prepared DELETE payload for {product_number}: {prepared_delete}")
                    try:
                        self.http.request(url, method="DELETE", json_data=prepared_delete)
                    except Exception as delete_error:
                        message = str(delete_error)
                        if "404" in message:
                            self.logger.info("Prispost fandtes ikke ved sletning for %s (ignorerer 404)", product_number)
                        else:
                            raise

                if update_payload:
                    prepared_update = self._prepare_payload(update_payload)
                    self.logger.debug(f"Prepared PUT payload for {product_number}: {prepared_update}")
                    self.http.request(url, method="PUT", json_data=prepared_update)

                if create_payload:
                    prepared_create = self._prepare_payload(create_payload)
                    self.logger.debug(f"Prepared POST payload for {product_number}: {prepared_create}")
                    self.http.request(url, method="POST", json_data=prepared_create)

            self.logger.info(f"Updated prices for {product_number}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update prices for {product_number}: {e}")
            return False
