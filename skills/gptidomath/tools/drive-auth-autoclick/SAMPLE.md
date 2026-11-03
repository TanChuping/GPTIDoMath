# Google Drive approval card structure

This is a generic structural sketch, not captured conversation HTML. Class
names other than the container token are omitted. The provider title is the
alert's first span. The tool description belongs to the alert.

```html
<div class="@container/approval-card">
  <div>
    <div role="alert">
      <div>
        <div>
          <svg><!-- provider icon --></svg>
          <span>Google Drive</span>
        </div>
        <div>
          <div>Allow ChatGPT to use Google Drive?</div>
          <div>
            ChatGPT will call Google Drive's TOOL_NAME tool.
            <button type="button">Details</button>
          </div>
        </div>
      </div>
    </div>
  </div>
  <form>
    <button type="button"><span>Always allow</span></button>
    <div>
      <button type="button">Deny <kbd>Esc</kbd></button>
      <div>
        <button type="submit">Allow once <kbd>Enter</kbd></button>
        <button type="button"><svg><!-- dropdown icon --></svg></button>
      </div>
    </div>
  </form>
</div>
```

Button order inside the form: **Always allow → Deny → Allow once → dropdown**.
Details is outside the form. The first action can instead read **始终允许**.
The observed action buttons do not provide stable names, labels, or test IDs.

When the UI changes, record only tags, nesting, selector attributes, generic
provider/tool placeholders, button labels, and order. Omit conversation text,
tool arguments, document names, account details, and identifiers. Similar
responsive class names on forms or descendants are not the card container;
match the exact class token on its div.
