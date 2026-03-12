
# Explicitly rebuild model to resolve recursive/deferred references for Pydantic v2
DownloadZipRequest.model_rebuild()


@router.post("/stats", response_model=ExportStatsResponse)
def get_export_stats(request: ExportPreviewRequest, db: Session = Depends(get_db)):
    """
    Get statistics about the selected models for export readiness.
    """
    if not request.model_ids:
        return ExportStatsResponse(
            total_models=0,
            models_with_pricing=0,
            models_missing_pricing=0,
            models_with_images=0,
            models_missing_images=0,
            equipment_types={}
        )

    models = db.query(Model.id, Model.equipment_type_id, Model.image_url).filter(
        Model.id.in_(request.model_ids)
    ).all()

    if not models:
        return ExportStatsResponse(
            total_models=0,
            models_with_pricing=0,
            models_missing_pricing=0,
            models_with_images=0,
            models_missing_images=0,
            equipment_types={}
        )

    model_ids = {m.id for m in models}

    models_with_snapshot = {
        row[0] for row in db.query(ModelPricingSnapshot.model_id).filter(
            ModelPricingSnapshot.model_id.in_(model_ids),
            ModelPricingSnapshot.marketplace == "amazon",
            ModelPricingSnapshot.variant_key == "choice_no_padding"
        )
    }

    equipment_type_ids = {m.equipment_type_id for m in models if m.equipment_type_id is not None}
    equipment_type_map = {}
    if equipment_type_ids:
        equipment_type_map = {
            row[0]: row[1] for row in db.query(EquipmentType.id, EquipmentType.name).filter(
                EquipmentType.id.in_(equipment_type_ids)
            )
        }

    models_with_pricing = 0
    models_missing_pricing = 0
    models_with_images = 0
    models_missing_images = 0
    equipment_type_counts = {}

    for model in models:
        if model.id in models_with_snapshot:
            models_with_pricing += 1
        else:
            models_missing_pricing += 1

        if model.image_url and model.image_url.strip():
            models_with_images += 1
        else:
            models_missing_images += 1

        eq_name = equipment_type_map.get(model.equipment_type_id)
        if eq_name:
            equipment_type_counts[eq_name] = equipment_type_counts.get(eq_name, 0) + 1

    return ExportStatsResponse(
        total_models=len(models),
        models_with_pricing=models_with_pricing,
        models_missing_pricing=models_missing_pricing,
        models_with_images=models_with_images,
        models_missing_images=models_missing_images,
        equipment_types=equipment_type_counts
    )


@router.get("/health")
def export_health_check(db: Session = Depends(get_db)):
    """
    Check if export system is healthy and configured.
    """
    template_count = db.query(AmazonProductType).count()
    equipment_type_count = db.query(EquipmentType).count()

    linked_count = db.query(EquipmentTypeProductType).count()

    cache_size = 0
    cache_obj = globals().get("HTTP_CACHE", None)
    if cache_obj is not None:
        try:
            cache_size = len(cache_obj)
        except (TypeError, AttributeError):
            cache_size = 0

    return {
        "status": "healthy",
        "templates_configured": template_count,
        "equipment_types": equipment_type_count,
        "equipment_types_with_templates": linked_count,
        "cache_size": cache_size
    }
