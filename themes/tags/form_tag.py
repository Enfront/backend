import sys

from typing import List, Optional, Dict, TextIO, Tuple

from liquid import Environment
from liquid.ast import ChildNode, BlockNode, Node
from liquid.builtin.drops import IterableDrop
from liquid.builtin.tags.for_tag import ForLoop
from liquid.builtin.tags.include_tag import TAG_INCLUDE
from liquid.context import Context, ReadOnlyChainMap
from liquid.expression import Expression, Literal, Identifier
from liquid.parse import expect, get_parser
from liquid.stream import TokenStream
from liquid.tag import Tag
from liquid.expressions import TokenStream as ExprTokenStream
from liquid.expressions.common import parse_string_literal, parse_unchained_identifier
from liquid.expressions.include.lex import tokenize
from liquid.expressions.filtered.parse import parse_obj
from liquid.token import (
    Token,
    TOKEN_TAG,
    TOKEN_EXPRESSION,
    TOKEN_IDENTIFIER,
    TOKEN_COMMA,
    TOKEN_COLON,
    TOKEN_EOF,
    TOKEN_STRING
)


TAG_FORM = sys.intern("form")
TAG_ENDFORM = sys.intern("endform")


class FormNode(Node):
    __slots__ = ("tok", "name", "var", "loop", "alias", "args", "block")
    tag = TAG_FORM
    end = TAG_ENDFORM

    def __init__(
        self,
        tok: Token,
        name: Expression,
        block: BlockNode,
        var: Optional[Expression] = None,
        loop: bool = False,
        alias: Optional[str] = None,
        args: Optional[Dict[str, Expression]] = None,
    ):
        self.tok = tok
        self.name = name
        self.block = block
        self.var = var
        self.loop = loop
        self.alias = alias
        self.args = args or {}

    def __str__(self) -> str:
        buf = [f"{self.name}"]

        if self.var:
            buf.append(f" with {self.var}")

        if self.alias:
            buf.append(f" as {self.alias}")

        if self.args:
            buf.append(", ")

        args = (f"{key}={val}" for key, val in self.args.items())
        buf.append(", ".join(args))

        return f"{self.tag}({''.join(buf)})"

    def __repr__(self) -> str:
        return f"RenderNode(tok={self.tok!r}, name={self.name})"  # pragma: no cover

    def render_to_output(self, context: Context, buffer: TextIO) -> Optional[bool]:
        file_name = self.name.evaluate(context)
        path = 'forms/' + str(file_name) + '.liquid'
        assert isinstance(path, str)
        template = context.get_template_with_context(path, tag=self.tag)

        # Evaluate keyword arguments once. Unlike 'include', 'render' can not
        # mutate variables in the outer scope, so there's no need to re-evaluate
        # arguments for each loop (if any).
        args = {k: v.evaluate(context) for k, v in self.args.items()}

        # We're using a chain map here in case we need to push a forloop drop into
        # it. As drops are read only, the built-in collections.ChainMap will not do.
        namespace = ReadOnlyChainMap(args)

        # New context with globals and filters from the parent, plus the read only
        # namespace containing render arguments and bound variable.
        ctx = context.copy(
            namespace,
            disabled_tags=[TAG_INCLUDE],
            carry_loop_iterations=True,
        )

        # Optionally bind a variable to the render namespace.
        if self.var is not None:
            val = self.var.evaluate(context)
            key = self.alias or template.name.split(".")[0]

            # If the variable is array-like, render the template once for each item.
            # `self.loop` being True indicates the render expression used "for" not
            # "with". This distinction is not made when using the 'include' tag.
            if self.loop and isinstance(val, (tuple, list, IterableDrop)):
                ctx.raise_for_loop_limit(len(val))
                forloop = ForLoop(
                    name=key,
                    it=iter(val),
                    length=len(val),
                    parentloop=context.env.undefined("parentloop"),
                )

                args["forloop"] = forloop
                args[key] = None

                for itm in forloop:
                    args[key] = itm
                    template.render_with_context(
                        ctx, buffer, partial=True, block_scope=True
                    )
            else:
                # The bound variable is not array-like, shove it into the namespace via args.
                args[key] = val
                template.render_with_context(
                    ctx, buffer, partial=True, block_scope=True
                )
        else:
            buffer.write(template.render(**args))
            self.block.render(context, buffer)
            buffer.write("\n</form>")

        return True

    def children(self) -> List[ChildNode]:
        block_scope: List[str] = list(self.args.keys())
        _children = [
            ChildNode(
                linenum=self.tok.linenum,
                node=None,
                expression=self.name,
                block_scope=block_scope,
                load_mode="render",
                load_context={"tag": "render"},
            )
        ]
        if self.var:
            if self.alias:
                block_scope.append(self.alias)
            elif isinstance(self.name, Literal):
                block_scope.append(str(self.name.value).split(".", 1)[0])
            _children.append(
                ChildNode(
                    linenum=self.tok.linenum,
                    expression=self.var,
                )
            )
        for expr in self.args.values():
            _children.append(ChildNode(linenum=self.tok.linenum, expression=expr))
        return _children


class FormTag(Tag):
    name = TAG_FORM
    node_class = FormNode
    block = False

    def __init__(self, env: Environment):
        super().__init__(env)
        self.parser = get_parser(self.env)

    def parse(self, stream: TokenStream) -> Node:
        tok = next(stream)
        expect(stream, TOKEN_EXPRESSION)
        expr_stream = ExprTokenStream(tokenize(stream.current.value))

        # Need a string. 'render' does not accept identifiers that resolve to a string.
        # This is the name of the template to be included.
        expr_stream.expect(TOKEN_STRING)
        name = parse_string_literal(expr_stream)
        expr_stream.next_token()

        alias: Optional[str] = None
        identifier: Optional[Identifier] = None
        loop: bool = False

        # Zero or more keyword arguments
        args = {}

        # The first keyword argument might follow immediately or after a comma.
        if expr_stream.current[1] == TOKEN_IDENTIFIER:
            key, val = parse_argument(expr_stream)
            args[key] = val

        while expr_stream.current[1] != TOKEN_EOF:
            if expr_stream.current[1] == TOKEN_COMMA:
                expr_stream.next_token()  # Eat comma
                key, val = parse_argument(expr_stream)
                args[key] = val
            else:
                break

        stream.next_token()
        block = self.parser.parse_block(stream, (TAG_ENDFORM, TOKEN_EOF))
        expect(stream, TOKEN_TAG, value=TAG_ENDFORM)

        return self.node_class(
            tok,
            name=name,
            var=identifier,
            loop=loop,
            alias=alias,
            args=args,
            block=block,
        )


def parse_argument(stream: ExprTokenStream) -> Tuple[str, Expression]:
    stream.expect(TOKEN_IDENTIFIER)

    if stream.peek[1] == TOKEN_COLON:
        key = str(parse_unchained_identifier(stream))
        stream.next_token()
        stream.expect(TOKEN_COLON)
        stream.next_token()  # Eat colon
        val = parse_obj(stream)
        stream.next_token()
    else:
        val = parse_obj(stream)
        key = str(val)
        stream.next_token()

    return key, val
