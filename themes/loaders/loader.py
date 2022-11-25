import os
import boto3

from liquid import Context
from liquid.exceptions import TemplateNotFound
from liquid.loaders import TemplateSource, FileExtensionLoader
from liquid.builtin.tags.include_tag import IncludeNode, IncludeTag


class FragmentNode(IncludeNode):
    tag = 'fragment'


class FragmentTag(IncludeTag):
    name = 'fragment'
    node_class = FragmentNode


class CustomFileSystemLoader(FileExtensionLoader):
    def get_source_with_context(self, context: Context, template_name: str, **kwargs: str) -> TemplateSource:
        if kwargs.get('tag') == 'fragment':
            s3 = boto3.client('s3')

            try:
                theme_template_path = os.path.join(
                    'themes',
                    'templates',
                    'official',
                    'portrait',
                    'fragments',
                    template_name + '.liquid'
                )

                section = s3.get_object(Bucket='jkpay', Key=theme_template_path)
                section_decoded = section['Body'].read().decode('utf_8')
            except s3.exceptions.NoSuchKey:
                raise TemplateNotFound(template_name)

            return TemplateSource(section_decoded, template_name, super()._uptodate)

        return super().get_source(context.env, template_name)
