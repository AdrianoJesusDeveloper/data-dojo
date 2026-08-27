from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("library", "0002_librarysource")]
    operations = [
        migrations.RenameIndex(
            model_name="bookchunk",
            old_name="library_boo_book_id_397ff8_idx",
            new_name="library_boo_book_id_2348ba_idx",
        )
    ]
