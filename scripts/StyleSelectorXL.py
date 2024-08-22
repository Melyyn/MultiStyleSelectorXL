import contextlib
import gradio as gr
from modules import scripts, shared, script_callbacks
from modules.ui_components import FormRow, FormColumn, FormGroup, ToolButton
import json
import os
import random

stylespath = ""


def get_json_content(file_path):
    try:
        with open(file_path, 'rt', encoding="utf-8") as file:
            json_data = json.load(file)
            return json_data
    except Exception as e:
        print(f"A Problem occurred: {str(e)}")


def read_sdxl_styles(json_data):
    if not isinstance(json_data, list):
        print("Error: input data must be a list")
        return None

    names = []
    for item in json_data:
        if isinstance(item, dict) and 'name' in item:
            names.append(item['name'])
    names.sort()
    return names


def getStyles():
    global stylespath
    json_path = os.path.join(scripts.basedir(), 'sdxl_styles.json')
    stylespath = json_path
    json_data = get_json_content(json_path)
    styles = read_sdxl_styles(json_data)
    return styles


def createPositive(styles, positive):
    json_data = get_json_content(stylespath)
    combined_prompt = positive

    try:
        if not isinstance(json_data, list):
            raise ValueError("Invalid JSON data. Expected a list of templates.")

        for style in styles:
            for template in json_data:
                if template['name'] == style:
                    combined_prompt = template['prompt'].replace('{prompt}', combined_prompt)

        return combined_prompt

    except Exception as e:
        print(f"An error occurred: {str(e)}")


def createNegative(styles, negative):
    json_data = get_json_content(stylespath)
    combined_negative_prompt = negative

    try:
        if not isinstance(json_data, list):
            raise ValueError("Invalid JSON data. Expected a list of templates.")

        for style in styles:
            for template in json_data:
                if template['name'] == style:
                    json_negative_prompt = template.get('negative_prompt', "")
                    if combined_negative_prompt:
                        combined_negative_prompt = f"{json_negative_prompt}, {combined_negative_prompt}" if json_negative_prompt else combined_negative_prompt
                    else:
                        combined_negative_prompt = json_negative_prompt

        return combined_negative_prompt

    except Exception as e:
        print(f"An error occurred: {str(e)}")


class StyleSelectorXL(scripts.Script):
    def __init__(self) -> None:
        super().__init__()

    styleNames = getStyles()

    def title(self):
        return "Style Selector for SDXL 1.0"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        enabled = getattr(shared.opts, "enable_styleselector_by_default", True)
        with gr.Group():
            with gr.Accordion("SDXL Styles", open=enabled):
                with FormRow():
                    with FormColumn(min_width=160):
                        is_enabled = gr.Checkbox(
                            value=enabled, label="Enable Style Selector", info="Enable Or Disable Style Selector ")
                    with FormColumn(elem_id="Randomize Style"):
                        randomize = gr.Checkbox(
                            value=False, label="Randomize Style", info="This Will Override Selected Style")
                    with FormColumn(elem_id="Randomize For Each Iteration"):
                        randomizeEach = gr.Checkbox(
                            value=False, label="Randomize For Each Iteration", info="Every prompt in Batch Will Have Random Style")

                with FormRow():
                    with FormColumn(min_width=160):
                        allstyles = gr.Checkbox(
                            value=False, label="Generate All Styles In Order", info="To Generate Your Prompt in All Available Styles, Its Better to set batch count to " + str(len(self.styleNames)) + " ( Style Count)")

                style_ui_type = shared.opts.data.get(
                    "styles_ui", "checkboxes")

                style = gr.CheckboxGroup(
                    label='Style', choices=self.styleNames, value=['base'])

        return [is_enabled, randomize, randomizeEach, allstyles, style]

    def process(self, p, is_enabled, randomize, randomizeEach, allstyles, styles):
        if not is_enabled:
            return

        if randomize:
            styles = [random.choice(self.styleNames)]
        batchCount = len(p.all_prompts)

        if(batchCount == 1):
            for i, prompt in enumerate(p.all_prompts):
                positivePrompt = createPositive(styles, prompt)
                p.all_prompts[i] = positivePrompt
            for i, prompt in enumerate(p.all_negative_prompts):
                negativePrompt = createNegative(styles, prompt)
                p.all_negative_prompts[i] = negativePrompt

        if(batchCount > 1):
            style_map = {}
            for i, prompt in enumerate(p.all_prompts):
                if(randomize):
                    style_map[i] = [random.choice(self.styleNames)]
                else:
                    style_map[i] = styles
                if(allstyles):
                    style_map[i] = [self.styleNames[i % len(self.styleNames)]]

            for i, prompt in enumerate(p.all_prompts):
                positivePrompt = createPositive(
                    style_map[i] if randomizeEach or allstyles else style_map[0], prompt)
                p.all_prompts[i] = positivePrompt
            for i, prompt in enumerate(p.all_negative_prompts):
                negativePrompt = createNegative(
                    style_map[i] if randomizeEach or allstyles else style_map[0], prompt)
                p.all_negative_prompts[i] = negativePrompt

        p.extra_generation_params["Style Selector Enabled"] = True
        p.extra_generation_params["Style Selector Randomize"] = randomize
        p.extra_generation_params["Style Selector Styles"] = styles

    def after_component(self, component, **kwargs):
        if kwargs.get("elem_id") == "txt2img_prompt":
            self.boxx = component
        if kwargs.get("elem_id") == "img2img_prompt":
            self.boxxIMG = component


def on_ui_settings():
    section = ("styleselector", "Style Selector")
    shared.opts.add_option("styles_ui", shared.OptionInfo(
        "checkboxes", "How should Style Names Rendered on UI", gr.CheckboxGroup, section=section))

    shared.opts.add_option(
        "enable_styleselector_by_default",
        shared.OptionInfo(
            True,
            "enable Style Selector by default",
            gr.Checkbox,
            section=section
        )
    )


script_callbacks.on_ui_settings(on_ui_settings)
