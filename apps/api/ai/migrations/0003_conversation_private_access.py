import uuid

from django.db import migrations, models


def populate_public_ids(apps, schema_editor):
    conversation_model = apps.get_model("ai", "Conversation")
    for conversation in conversation_model.objects.filter(public_id__isnull=True).iterator():
        conversation.public_id = uuid.uuid4()
        conversation.save(update_fields=["public_id"])


class Migration(migrations.Migration):
    dependencies = [("ai", "0002_public_sales_conversation")]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="public_id",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="conversation",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="conversation",
            name="anonymous_access_hash",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
