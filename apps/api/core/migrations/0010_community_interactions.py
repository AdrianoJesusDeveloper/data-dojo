from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0009_alter_user_profile_picture")]

    operations = [
        migrations.AddField(model_name="forumtopic", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.AddField(model_name="forumcomment", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.AddField(model_name="forumcomment", name="likes", field=models.ManyToManyField(blank=True, related_name="liked_forum_comments", to="core.user")),
    ]
