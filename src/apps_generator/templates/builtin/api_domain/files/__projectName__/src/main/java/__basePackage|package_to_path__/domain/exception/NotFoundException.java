package {{ basePackage }}.domain.exception;

/**
 * Thrown when a requested resource does not exist (or is not visible to the current tenant).
 */
public class NotFoundException extends RuntimeException {

    private final String resourceType;
    private final Object resourceId;

    public NotFoundException(String resourceType, Object resourceId) {
        super(resourceType + " not found: " + resourceId);
        this.resourceType = resourceType;
        this.resourceId = resourceId;
    }

    public String getResourceType() {
        return resourceType;
    }

    public Object getResourceId() {
        return resourceId;
    }
}
