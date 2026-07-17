from __future__ import annotations

from django import forms

from ai_visibility.teams.models import IntegrationConfig

# Which credential key each provider stores its secret under.
CRED_KEYS = {
    "github": "token",
    "newrelic": "api_key",
    "sonarqube": "token",
    "jira": "token",
    "anthropic": "api_key",
}


class IntegrationForm(forms.ModelForm):
    secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Leave blank to keep the current credential.",
    )

    class Meta:
        model = IntegrationConfig
        fields = ["enabled", "config"]

    def save(self, *, commit: bool = True) -> IntegrationConfig:
        instance = super().save(commit=False)
        secret = self.cleaned_data.get("secret")
        if secret:
            key = CRED_KEYS.get(instance.provider, "token")
            instance.set_credentials({key: secret})
        if commit:
            instance.save()
        return instance
