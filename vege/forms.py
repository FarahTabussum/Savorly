from django import forms

from .models import recipe


class RecipeForm(forms.ModelForm):
    """Form used by chefs to add a recipe.

    The public model uses ``name`` while the recipe form has historically used
    ``recipe_name`` in its POST data.  Keeping that field name makes the form
    backwards compatible while still providing normal model-form validation.
    """

    recipe_name = forms.CharField(
        label="Recipe Name",
        max_length=100,
        required=True,
    )

    class Meta:
        model = recipe
        fields = ("recipe_name", "recipe_description", "recipe_image")
        widgets = {
            "recipe_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Tell us about this dish",
                    "required": True,
                }
            ),
            "recipe_image": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": "image/*"}
            ),
        }

    def save(self, commit=True):
        new_recipe = super().save(commit=False)
        new_recipe.name = self.cleaned_data["recipe_name"]

        if commit:
            new_recipe.save()
            self.save_m2m()

        return new_recipe
